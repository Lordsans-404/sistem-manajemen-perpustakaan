import logging
from datetime import date, timedelta

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
    - BookCopy must not currently be pending or active (not available).
    - due_date must be strictly after borrow_date.
    """
    if not member.is_verified:
        raise ValueError("Member is not verified. Only verified members can borrow books.")

    today = date.today()
    effective_borrow_date = borrow_date or today

    if due_date <= effective_borrow_date:
        raise ValueError("due_date must be after borrow_date.")

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


def return_book(*, borrow: BorrowTransaction, return_date: date) -> BorrowTransaction:
    """
    Mark a borrowed book as returned.
    Transitions: ACTIVE → RETURNED.
    Auto-creates an overdue fine if the book is returned late.

    Raises ValueError if:
    - Transaction is not ACTIVE (cannot return pending/failed/already returned).
    - return_date is in the future.
    """
    if borrow.status != BorrowTransaction.Status.ACTIVE:
        raise ValueError(
            f"Cannot return a transaction with status '{borrow.status}'. "
            "Only active transactions can be returned."
        )

    if return_date > date.today():
        raise ValueError("return_date cannot be in the future.")

    with transaction.atomic():
        borrow.return_date = return_date
        borrow.status = BorrowTransaction.Status.RETURNED
        borrow.save(update_fields=["return_date", "status", "updated_at"])

        # Auto-create overdue fine if returned late
        if return_date > borrow.due_date:
            overdue_days = (return_date - borrow.due_date).days
            fine_amount = _calculate_overdue_fine(overdue_days)
            Fine.objects.create(
                borrow_transaction=borrow,
                fine_type=Fine.FineType.OVERDUE,
                amount=fine_amount,
                description=f"Late return — {overdue_days} day(s) overdue.",
            )
            logger.info(
                "fine.auto_created borrow_id=%s overdue_days=%s amount=%s",
                borrow.pk, overdue_days, fine_amount,
            )

    logger.info(
        "borrow.returned borrow_id=%s return_date=%s",
        borrow.pk, return_date,
    )
    return borrow


def _calculate_overdue_fine(overdue_days: int) -> int:
    """
    Calculate overdue fine amount in IDR.
    Rate: Rp 1.000 per day (configurable via Django settings).
    """
    from django.conf import settings
    rate = getattr(settings, "FINE_PER_DAY_IDR", 1000)
    return overdue_days * rate