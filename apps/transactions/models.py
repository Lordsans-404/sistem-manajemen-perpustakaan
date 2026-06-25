import uuid
from datetime import date

from django.db import models

from apps.catalog.models import BookCopy
from apps.users.models import Library, MemberProfile, TimestampMixin


# ---------------------------------------------------------------------------
# BorrowTransaction
# ---------------------------------------------------------------------------


class BorrowTransaction(TimestampMixin):
    """Records a single book borrowing event by a member."""

    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending"   # created, waiting for staff approval
        ACTIVE   = "active",   "Active"    # approved by staff, book handed over
        RETURNED = "returned", "Returned"  # book returned by member
        FAILED   = "failed",   "Failed"    # expired (>1 day pending) or rejected by staff

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.PROTECT,
        related_name="borrow_transactions",
    )
    book_copy = models.ForeignKey(
        BookCopy,
        on_delete=models.PROTECT,
        related_name="borrow_transactions",
    )
    library = models.ForeignKey(
        Library,
        on_delete=models.PROTECT,
        related_name="borrow_transactions",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Lifecycle status of this borrow transaction.",
    )
    borrow_date = models.DateField(default=date.today)
    due_date = models.DateField()
    return_date = models.DateField(
        null=True,
        blank=True,
        help_text="Filled in when the book is returned.",
    )

    class Meta:
        db_table = "borrow_transactions"
        verbose_name = "Borrow Transaction"
        verbose_name_plural = "Borrow Transactions"
        ordering = ["-borrow_date"]

    def __str__(self):
        return (
            f"{self.member.user.name} — "
            f"{self.book_copy.book.title} [{self.get_status_display()}]"
        )

    @property
    def is_overdue(self) -> bool:
        """True if the book is active, not yet returned, and due date has passed."""
        if self.status != self.Status.ACTIVE:
            return False
        if self.return_date:
            return False
        return date.today() > self.due_date

    @property
    def overdue_days(self) -> int:
        """Number of days overdue. Returns 0 if not overdue or already returned."""
        if self.return_date or not self.is_overdue:
            return 0
        return (date.today() - self.due_date).days


# ---------------------------------------------------------------------------
# Fine
# ---------------------------------------------------------------------------


class Fine(TimestampMixin):
    """
    Fine imposed on a member linked to a single borrow transaction.
    fine_type distinguishes the reason — overdue fines are auto-generated
    by the return service; damage / loss / other are created manually by staff.
    """

    class FineType(models.TextChoices):
        OVERDUE = "overdue", "Overdue"   # auto-generated on late return
        DAMAGE  = "damage",  "Damage"    # book returned in damaged condition
        LOSS    = "loss",    "Loss"      # book declared lost
        OTHER   = "other",   "Other"     # any other reason

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID   = "paid",   "Paid"
        WAIVED = "waived", "Waived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    borrow_transaction = models.ForeignKey(
        BorrowTransaction,
        on_delete=models.CASCADE,
        related_name="fines",
    )
    fine_type = models.CharField(
        max_length=10,
        choices=FineType.choices,
        default=FineType.OVERDUE,
        db_index=True,
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Optional notes from staff explaining the reason for this fine.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Fine amount in IDR.",
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the fine was settled.",
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
    )

    class Meta:
        db_table = "fines"
        verbose_name = "Fine"
        verbose_name_plural = "Fines"
        constraints = [
            models.UniqueConstraint(
                fields=["borrow_transaction", "fine_type"],
                condition=models.Q(fine_type="overdue"),
                name="unique_overdue_fine_per_transaction",
            )
        ]

    def __str__(self):
        return (
            f"Fine for {self.borrow_transaction} — "
            f"IDR {self.amount:,.0f} [{self.get_payment_status_display()}]"
    )