from rest_framework import serializers

from apps.transactions.models import Fine
from apps.transactions.serializers.borrow_serializers import BorrowTransactionListOutputSerializer


# ---------------------------------------------------------------------------
# Fine — Input
# ---------------------------------------------------------------------------


class FineInputSerializer(serializers.Serializer):
    """Validates data for creating a Fine record on a borrow transaction."""

    borrow_transaction_id = serializers.UUIDField(
        help_text="UUID of the BorrowTransaction this fine is associated with."
    )
    fine_type = serializers.ChoiceField(
        choices=Fine.FineType.choices,
        default=Fine.FineType.OVERDUE,
        help_text="Reason for the fine. 'overdue' is auto-generated; others are set manually by staff.",
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        help_text="Fine amount in IDR.",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Staff notes explaining the reason (required for damage / loss / other).",
    )

    def validate_borrow_transaction_id(self, value):
        """Prevent duplicate fine for the same borrow transaction."""
        from apps.transactions.models import BorrowTransaction

        if not BorrowTransaction.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Borrow transaction not found.")
        if Fine.objects.filter(borrow_transaction_id=value).exists():
            raise serializers.ValidationError("A fine already exists for this borrow transaction.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Description is required when fine_type is not overdue."""
        fine_type = attrs.get("fine_type", Fine.FineType.OVERDUE)
        description = attrs.get("description")
        if fine_type != Fine.FineType.OVERDUE and not description:
            raise serializers.ValidationError(
                {"description": "description is required for damage, loss, or other fine types."}
            )
        return attrs


class FinePaymentInputSerializer(serializers.Serializer):
    """Validates data for settling or waiving a Fine."""

    payment_status = serializers.ChoiceField(
        choices=[
            Fine.PaymentStatus.PAID,
            Fine.PaymentStatus.WAIVED,
        ],
        help_text="New payment status — 'paid' or 'waived'.",
    )
    paid_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Date the fine was settled (required when status is 'paid').",
    )

    def validate(self, attrs: dict) -> dict:
        if attrs.get("payment_status") == Fine.PaymentStatus.PAID and not attrs.get("paid_date"):
            raise serializers.ValidationError({"paid_date": "paid_date is required when payment_status is 'paid'."})
        return attrs


# ---------------------------------------------------------------------------
# Fine — Output
# ---------------------------------------------------------------------------


class FineOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a Fine, includes nested transaction summary."""

    borrow_transaction = BorrowTransactionListOutputSerializer(read_only=True)

    class Meta:
        model = Fine
        fields = [
            "id",
            "borrow_transaction",
            "fine_type",
            "description",
            "amount",
            "paid_date",
            "payment_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
