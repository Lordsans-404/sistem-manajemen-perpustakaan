import logging
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import BookCopy
from apps.transactions.models import BorrowTransaction, Fine
from apps.users.models import Library, MemberProfile

logger = logging.getLogger(__name__)


def create_borrow_transaction(
    *,
    member: MemberProfile,
    book_copy: BookCopy,
    library: Library,
    due_date: date,
    borrow_date: date | None = None,
) -> BorrowTransaction:
    """
    Record a new book borrowing request.
    Status starts as PENDING — staff must approve before book is handed over.

    Business rules enforced here:
    - Member must be verified.
    - Member must not have unpaid fines.
    - Member must not exceed the active borrow limit (max 5 PENDING + ACTIVE).
    - BookCopy condition must not be 'lost'.
    - BookCopy must not currently be pending or active (not available).
    - due_date must be strictly after borrow_date.
    """
    if not member.is_verified:
        raise ValueError("Member is not verified. Only verified members can borrow books.")

    today = date.today()
    effective_borrow_date = borrow_date or today

    if due_date <= effective_borrow_date:
        raise ValueError("due_date must be after borrow_date.")

    if book_copy.condition == BookCopy.Condition.LOST:
        raise ValueError(f"Cannot borrow book copy '{book_copy.pk}' because its condition is 'lost'.")

    # Check if member has unpaid fines
    has_unpaid_fines = Fine.objects.filter(
        borrow_transaction__member=member,
        payment_status=Fine.PaymentStatus.UNPAID
    ).exists()
    if has_unpaid_fines:
        raise ValueError("Member has unpaid fines and cannot borrow new books until they are paid.")

    # Check active borrow limit (configurable via BORROW_MAX_ACTIVE_BOOKS env var)
    max_borrows = settings.BORROW_MAX_ACTIVE_BOOKS
    active_borrow_count = BorrowTransaction.objects.filter(
        member=member,
        status__in=[
            BorrowTransaction.Status.PENDING,
            BorrowTransaction.Status.ACTIVE,
        ],
    ).count()
    if active_borrow_count >= max_borrows:
        raise ValueError(
            f"Member has reached the maximum borrow limit of {max_borrows} books. "
            "Return or resolve existing borrows before borrowing more."
        )

    # Guard against double-borrowing — block if copy has pending or active transaction.
    # (failed/returned transactions are fine — book is available again)
    unavailable = BorrowTransaction.objects.filter(
        book_copy=book_copy,
        status__in=[
            BorrowTransaction.Status.PENDING,
            BorrowTransaction.Status.ACTIVE,
        ],
    ).exists()

    if unavailable:
        raise ValueError(
            f"Book copy '{book_copy.pk}' is currently unavailable."
        )

    with transaction.atomic():
        borrow = BorrowTransaction.objects.create(
            member=member,
            book_copy=book_copy,
            library=library,
            borrow_date=effective_borrow_date,
            due_date=due_date,
            status=BorrowTransaction.Status.PENDING,
        )

    logger.info(
        "borrow.created borrow_id=%s member_id=%s copy_id=%s due=%s status=pending",
        borrow.pk, member.pk, book_copy.pk, due_date,
    )
    return borrow


def approve_borrow(*, borrow: BorrowTransaction) -> BorrowTransaction:
    """
    Staff approves a pending borrow request.
    Transitions: PENDING → ACTIVE.

    Raises ValueError if:
    - Transaction is not in PENDING status.
    """
    if borrow.status != BorrowTransaction.Status.PENDING:
        raise ValueError(
            f"Cannot approve a transaction with status '{borrow.status}'. "
            "Only pending transactions can be approved."
        )

    borrow.status = BorrowTransaction.Status.ACTIVE
    borrow.save(update_fields=["status", "updated_at"])

    logger.info(
        "borrow.approved borrow_id=%s member_id=%s copy_id=%s",
        borrow.pk, borrow.member.pk, borrow.book_copy.pk,
    )
    return borrow


def reject_borrow(*, borrow: BorrowTransaction) -> BorrowTransaction:
    """
    Staff rejects a pending borrow request.
    Transitions: PENDING → FAILED.
    Member must create a new transaction to try again.

    Raises ValueError if:
    - Transaction is not in PENDING status.
    """
    if borrow.status != BorrowTransaction.Status.PENDING:
        raise ValueError(
            f"Cannot reject a transaction with status '{borrow.status}'. "
            "Only pending transactions can be rejected."
        )

    borrow.status = BorrowTransaction.Status.FAILED
    borrow.save(update_fields=["status", "updated_at"])

    logger.info(
        "borrow.rejected borrow_id=%s member_id=%s copy_id=%s",
        borrow.pk, borrow.member.pk, borrow.book_copy.pk,
    )
    return borrow


def expire_pending_borrows() -> int:
    """
    Mark all PENDING transactions older than 1 day as FAILED.
    Intended to be called by a management command + Cloud Scheduler daily.

    Returns the number of transactions expired.
    """
    expiry_threshold = timezone.now() - timedelta(days=1)

    expired_count = BorrowTransaction.objects.filter(
        status=BorrowTransaction.Status.PENDING,
        created_at__lt=expiry_threshold,
    ).update(
        status=BorrowTransaction.Status.FAILED,
    )

    if expired_count:
        logger.info("borrow.expired count=%s", expired_count)

    return expired_count


def update_borrow_status(*, borrow: BorrowTransaction, new_status: str) -> BorrowTransaction:
    """
    Manually override the status of a borrow transaction.
    Intended for staff to correct mistakes (e.g. FAILED -> PENDING).
    """
    if new_status not in BorrowTransaction.Status.values:
        raise ValueError(f"Invalid status: '{new_status}'.")

    borrow.status = new_status
    borrow.save(update_fields=["status", "updated_at"])

    logger.info("borrow.status_updated borrow_id=%s new_status=%s", borrow.pk, new_status)
    return borrow
