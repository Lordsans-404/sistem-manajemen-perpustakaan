from apps.transactions.models import Fine


def get_fine_by_id(fine_id):
    """Return a Fine by PK with borrow_transaction and related objects, or None."""
    return (
        Fine.objects
        .select_related(
            "borrow_transaction__member__user",
            "borrow_transaction__book_copy__book",
            "borrow_transaction__library",
        )
        .filter(pk=fine_id)
        .first()
    )


def get_fine_by_borrow(borrow_id):
    """Return the Fine linked to a specific borrow transaction, or None."""
    return (
        Fine.objects
        .select_related(
            "borrow_transaction__member__user",
            "borrow_transaction__book_copy__book",
            "borrow_transaction__library",
        )
        .filter(borrow_transaction_id=borrow_id)
        .first()
    )


def get_fines_by_member(member_id):
    """Return all fines for a member, newest first."""
    return (
        Fine.objects
        .select_related(
            "borrow_transaction__member__user",
            "borrow_transaction__book_copy__book",
            "borrow_transaction__library",
        )
        .filter(borrow_transaction__member_id=member_id)
        .order_by("-created_at")
    )


def get_all_fines(payment_status: str | None = None):
    """
    Return all fines with related objects pre-fetched.
    Optionally filter by payment_status ('unpaid', 'paid', 'waived').
    """
    qs = (
        Fine.objects
        .select_related(
            "borrow_transaction__member__user",
            "borrow_transaction__book_copy__book",
            "borrow_transaction__library",
        )
        .order_by("-created_at")
    )
    if payment_status:
        qs = qs.filter(payment_status=payment_status)
    return qs


def get_unpaid_fines_by_member(member_id):
    """Return all unpaid fines for a specific member."""
    return (
        Fine.objects
        .select_related(
            "borrow_transaction__member__user",
            "borrow_transaction__book_copy__book",
            "borrow_transaction__library",
        )
        .filter(
            borrow_transaction__member_id=member_id,
            payment_status=Fine.PaymentStatus.UNPAID,
        )
        .order_by("-created_at")
    )
