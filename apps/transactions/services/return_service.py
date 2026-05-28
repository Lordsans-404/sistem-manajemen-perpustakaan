import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.transactions.models import BorrowTransaction, Fine

logger = logging.getLogger(__name__)

# Rate charged per overdue day in IDR
DAILY_FINE_RATE: Decimal = Decimal("1000.00")


def return_book(*, borrow: BorrowTransaction, return_date: date) -> BorrowTransaction:
    """
    Mark a borrow transaction as returned and auto-create an overdue fine if needed.

    Business rules:
    - The borrow must not already be returned.
    - return_date cannot be in the future.
    - If the book is returned late, an overdue Fine is automatically created
      using DAILY_FINE_RATE × overdue_days.
    - If a fine already exists (idempotency guard), no duplicate is created.

    Returns the updated BorrowTransaction instance.
    """
    if borrow.return_date is not None:
        raise ValueError("This borrow transaction has already been returned.")

    today = date.today()
    if return_date > today:
        raise ValueError("return_date cannot be in the future.")

    with transaction.atomic():
        borrow.return_date = return_date
        borrow.save(update_fields=["return_date", "updated_at"])

        # Auto-create overdue fine when book is returned late
        if return_date > borrow.due_date:
            _create_overdue_fine(borrow=borrow, return_date=return_date)

    logger.info(
        "borrow.returned borrow_id=%s return_date=%s overdue=%s",
        borrow.pk, return_date, return_date > borrow.due_date,
    )
    return borrow


def _create_overdue_fine(*, borrow: BorrowTransaction, return_date: date) -> Fine | None:
    """
    Internal helper — create an overdue Fine for a late return.
    Idempotent: returns None without raising if a Fine already exists.
    """
    if Fine.objects.filter(borrow_transaction=borrow).exists():
        logger.warning(
            "fine.already_exists borrow_id=%s — skipping duplicate overdue fine",
            borrow.pk,
        )
        return None

    overdue_days = (return_date - borrow.due_date).days
    amount = DAILY_FINE_RATE * overdue_days

    fine = Fine.objects.create(
        borrow_transaction=borrow,
        fine_type=Fine.FineType.OVERDUE,
        amount=amount,
        payment_status=Fine.PaymentStatus.UNPAID,
    )

    logger.info(
        "fine.created_overdue fine_id=%s borrow_id=%s days=%d amount=%s",
        fine.pk, borrow.pk, overdue_days, amount,
    )
    return fine
