from datetime import date

from apps.transactions.models import BorrowTransaction, Fine

# Shared select_related chain — used by all selectors to avoid N+1 queries.
_BORROW_SELECT_RELATED = [
    "member__user",
    "book_copy__book",
    "book_copy__library",
    "library",
]


def get_borrow_by_id(borrow_id):
    """Return a BorrowTransaction by PK with all related objects, or None."""
    return (
        BorrowTransaction.objects
        .select_related(*_BORROW_SELECT_RELATED)
        .prefetch_related("fines")
        .filter(pk=borrow_id)
        .first()
    )


def get_all_borrows(status: str | None = None):
    """
    Return all borrow transactions with related objects pre-fetched.

    Pass status to filter by a specific status:
      'pending'  → waiting for staff approval
      'active'   → approved, book handed over
      'returned' → book returned
      'failed'   → expired or rejected
    Pass None to return all statuses.
    """
    qs = (
        BorrowTransaction.objects
        .select_related(*_BORROW_SELECT_RELATED)
        .prefetch_related("fines")
        .order_by("-borrow_date")
    )

    if status is not None:
        qs = qs.filter(status=status)

    return qs


def get_borrows_by_member(member_id, status: str | None = None):
    """
    Return all borrow transactions for a member, newest first.
    Optionally filter by status.
    """
    qs = (
        BorrowTransaction.objects
        .select_related(*_BORROW_SELECT_RELATED)
        .prefetch_related("fines")
        .filter(member_id=member_id)
        .order_by("-borrow_date")
    )

    if status is not None:
        qs = qs.filter(status=status)

    return qs


def get_overdue_borrows():
    """
    Return all currently overdue borrow transactions.
    Overdue = status is ACTIVE and due_date < today.
    """
    return (
        BorrowTransaction.objects
        .select_related(*_BORROW_SELECT_RELATED)
        .prefetch_related("fines")
        .filter(
            status=BorrowTransaction.Status.ACTIVE,
            due_date__lt=date.today(),
        )
        .order_by("due_date")
    )


def get_borrows_with_unpaid_fine(member_id=None):
    """
    Return returned transactions that have at least one unpaid fine.
    Optionally filter by member_id.

    Use case: staff checks who still has outstanding fines,
    or member checks their own unpaid fines.
    """
    qs = (
        BorrowTransaction.objects
        .select_related(*_BORROW_SELECT_RELATED)
        .prefetch_related("fines")
        .filter(
            status=BorrowTransaction.Status.RETURNED,
            fines__payment_status=Fine.PaymentStatus.UNPAID,
        )
        .distinct()  # prevent duplicates if multiple unpaid fines exist
        .order_by("-borrow_date")
    )

    if member_id is not None:
        qs = qs.filter(member_id=member_id)

    return qs


def get_unavailable_borrow_for_copy(book_copy_id):
    """
    Return the pending or active borrow for a specific book copy, or None.
    Used to check if a copy is currently unavailable before creating a new borrow.
    """
    return (
        BorrowTransaction.objects
        .select_related("member__user", "book_copy__book", "library")
        .filter(
            book_copy_id=book_copy_id,
            status__in=[
                BorrowTransaction.Status.PENDING,
                BorrowTransaction.Status.ACTIVE,
            ],
        )
        .first()
    )