import logging
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.transactions.models import BorrowTransaction, Fine

logger = logging.getLogger(__name__)


def create_manual_fine(
    *,
    borrow: BorrowTransaction,
    fine_type: str,
    amount: Decimal,
    description: str,
) -> Fine:
    """
    Create a staff-initiated fine (damage, loss, other).
    Only one Fine is allowed per BorrowTransaction (OneToOne constraint).
    Raises ValueError if a fine already exists for this transaction.
    """
    if fine_type == Fine.FineType.OVERDUE:
        raise ValueError(
            "Overdue fines are created automatically by the return service. "
            "Use fine_type 'damage', 'loss', or 'other' for manual fines."
        )

    if Fine.objects.filter(borrow_transaction=borrow).exists():
        raise ValueError(
            f"A fine already exists for borrow transaction '{borrow.pk}'."
        )

    if not description or not description.strip():
        raise ValueError("description is required for non-overdue fines.")

    with transaction.atomic():
        fine = Fine.objects.create(
            borrow_transaction=borrow,
            fine_type=fine_type,
            amount=amount,
            description=description.strip(),
            payment_status=Fine.PaymentStatus.UNPAID,
        )

    logger.info(
        "fine.created_manual fine_id=%s borrow_id=%s type=%s amount=%s",
        fine.pk, borrow.pk, fine_type, amount,
    )
    return fine


def pay_fine(*, fine: Fine, paid_date: date) -> Fine:
    """
    Mark a fine as paid.
    Raises ValueError if the fine is already paid or waived.
    """
    if fine.payment_status != Fine.PaymentStatus.UNPAID:
        raise ValueError(
            f"Fine '{fine.pk}' is already '{fine.payment_status}' and cannot be paid again."
        )

    today = date.today()
    if paid_date > today:
        raise ValueError("paid_date cannot be in the future.")

    fine.payment_status = Fine.PaymentStatus.PAID
    fine.paid_date = paid_date
    fine.save(update_fields=["payment_status", "paid_date", "updated_at"])

    logger.info("fine.paid fine_id=%s paid_date=%s", fine.pk, paid_date)
    return fine


def waive_fine(*, fine: Fine) -> Fine:
    """
    Waive a fine (e.g. by decision of the librarian or supervisor).
    Raises ValueError if the fine has already been settled.
    """
    if fine.payment_status != Fine.PaymentStatus.UNPAID:
        raise ValueError(
            f"Fine '{fine.pk}' is already '{fine.payment_status}' and cannot be waived."
        )

    fine.payment_status = Fine.PaymentStatus.WAIVED
    fine.save(update_fields=["payment_status", "updated_at"])

    logger.info("fine.waived fine_id=%s", fine.pk)
    return fine
