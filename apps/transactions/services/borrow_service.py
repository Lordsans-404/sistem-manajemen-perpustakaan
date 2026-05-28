import logging
from datetime import date

from django.db import transaction

from apps.catalog.models import BookCopy
from apps.transactions.models import BorrowTransaction
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
    Record a new book borrowing event.

    Business rules enforced here:
    - Member must be verified.
    - BookCopy must not currently be on loan (no active unreturned transaction).
    - due_date must be strictly in the future.
    """
    if not member.is_verified:
        raise ValueError("Member is not verified. Only verified members can borrow books.")

    today = date.today()
    effective_borrow_date = borrow_date or today

    if due_date <= effective_borrow_date:
        raise ValueError("due_date must be after borrow_date.")

    # Guard against double-borrowing the same copy
    active_loan = (
        BorrowTransaction.objects
        .filter(book_copy=book_copy, return_date__isnull=True)
        .exists()
    )
    if active_loan:
        raise ValueError(
            f"Book copy '{book_copy.pk}' is currently on loan and cannot be borrowed."
        )

    with transaction.atomic():
        borrow = BorrowTransaction.objects.create(
            member=member,
            book_copy=book_copy,
            library=library,
            borrow_date=effective_borrow_date,
            due_date=due_date,
        )

    logger.info(
        "borrow.created borrow_id=%s member_id=%s copy_id=%s due=%s",
        borrow.pk, member.pk, book_copy.pk, due_date,
    )
    return borrow
