from apps.transactions.models import BorrowTransaction


def get_borrow_by_id(borrow_id):
    """Return a BorrowTransaction by PK with all related objects, or None."""
    return (
        BorrowTransaction.objects
        .select_related(
            "member__user",
            "book_copy__book",
            "book_copy__library",
            "library",
        )
        .filter(pk=borrow_id)
        .first()
    )


def get_borrows_by_member(member_id):
    """Return all borrow transactions for a member, newest first."""
    return (
        BorrowTransaction.objects
        .select_related(
            "member__user",
            "book_copy__book",
            "book_copy__library",
            "library",
        )
        .filter(member_id=member_id)
        .order_by("-borrow_date")
    )


def get_active_borrows_by_member(member_id):
    """Return currently unreturned borrows for a member (return_date is NULL)."""
    return (
        BorrowTransaction.objects
        .select_related(
            "member__user",
            "book_copy__book",
            "book_copy__library",
            "library",
        )
        .filter(member_id=member_id, return_date__isnull=True)
        .order_by("due_date")
    )


def get_all_borrows(returned: bool | None = None):
    """
    Return all borrow transactions with related objects pre-fetched.
    Pass returned=True to filter only returned borrows.
    Pass returned=False to filter only active borrows.
    """
    qs = BorrowTransaction.objects.select_related(
        "member__user",
        "book_copy__book",
        "book_copy__library",
        "library",
    ).order_by("-borrow_date")

    if returned is True:
        qs = qs.exclude(return_date__isnull=True)
    elif returned is False:
        qs = qs.filter(return_date__isnull=True)
    return qs


def get_overdue_borrows():
    """
    Return all currently overdue borrow transactions.
    Overdue means: return_date is NULL and due_date < today.
    """
    from datetime import date
    return (
        BorrowTransaction.objects
        .select_related(
            "member__user",
            "book_copy__book",
            "book_copy__library",
            "library",
        )
        .filter(return_date__isnull=True, due_date__lt=date.today())
        .order_by("due_date")
    )


def get_active_borrow_for_copy(book_copy_id):
    """Return the active (unreturned) borrow for a specific book copy, or None."""
    return (
        BorrowTransaction.objects
        .select_related("member__user", "book_copy__book", "library")
        .filter(book_copy_id=book_copy_id, return_date__isnull=True)
        .first()
    )
