import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.transactions.models import BorrowTransaction, Fine

logger = logging.getLogger(__name__)


def return_book(*, borrow: BorrowTransaction, return_date: date) -> BorrowTransaction:
    """
    Mark a borrow transaction as returned and auto-create an overdue fine if needed.

    Business rules:
    - The borrow must be in ACTIVE status.
    - return_date cannot be in the future.
    - return_date cannot be before borrow_date.
    - If the book is returned late, an overdue Fine is automatically created.
    - If an OVERDUE fine already exists (idempotency guard), no duplicate is created.

    Returns the updated BorrowTransaction instance.
    """
    if borrow.return_date is not None or borrow.status == BorrowTransaction.Status.RETURNED:
        raise ValueError("This borrow transaction has already been returned.")

    if borrow.status != BorrowTransaction.Status.ACTIVE:
        raise ValueError(
            f"Cannot return a transaction with status '{borrow.status}'. "
            "Only active transactions can be returned."
        )

    today = date.today()
    if return_date > today:
        raise ValueError("return_date cannot be in the future.")

    if return_date < borrow.borrow_date:
        raise ValueError("return_date cannot be before the borrow_date.")

    with transaction.atomic():
        borrow.return_date = return_date
        borrow.status = BorrowTransaction.Status.RETURNED
        borrow.save(update_fields=["return_date", "status", "updated_at"])

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
    Idempotent: returns None without raising if an OVERDUE Fine already exists.
    """
    if Fine.objects.filter(borrow_transaction=borrow, fine_type=Fine.FineType.OVERDUE).exists():
        logger.warning(
            "fine.already_exists borrow_id=%s — skipping duplicate overdue fine",
            borrow.pk,
        )
        return None

    overdue_days = (return_date - borrow.due_date).days
    rate = settings.FINE_PER_DAY_IDR
    amount = Decimal(rate * overdue_days)
    try:
        with transaction.atomic():
            fine = Fine.objects.create(
                borrow_transaction=borrow,
                fine_type=Fine.FineType.OVERDUE,
                amount=amount,
                payment_status=Fine.PaymentStatus.UNPAID,
                description=f"Late return — {overdue_days} day(s) overdue.",
            )   
            
    except IntegrityError:
        logger.warning(
            "fine.integrity_error borrow_id=%s — skipping duplicate overdue fine",
            borrow.pk,
        )
        return None

    logger.info(
        "fine.created_overdue fine_id=%s borrow_id=%s days=%d amount=%s",
        fine.pk, borrow.pk, overdue_days, amount,
    )
    return fine
