from rest_framework import serializers

from apps.catalog.serializers.book_copy_serializers import BookCopyOutputSerializer
from apps.transactions.models import BorrowTransaction
from apps.users.serializers.library_serializers import LibraryOutputSerializer
from apps.users.serializers.member_serializers import MemberProfileOutputSerializer


# ---------------------------------------------------------------------------
# BorrowTransaction — Input
# ---------------------------------------------------------------------------


class BorrowTransactionInputSerializer(serializers.Serializer):
    """Validates data required to create a new borrow transaction."""

    member_id = serializers.UUIDField(help_text="UUID of the MemberProfile borrowing the book.")
    book_copy_id = serializers.UUIDField(help_text="UUID of the specific BookCopy to be borrowed.")
    library_id = serializers.UUIDField(help_text="UUID of the Library where the transaction occurs.")
    due_date = serializers.DateField(help_text="Expected return date (YYYY-MM-DD).")

    def validate(self, attrs: dict) -> dict:
        """Ensure due_date is in the future relative to borrow_date."""
        from datetime import date

        due_date = attrs.get("due_date")
        if due_date and due_date <= date.today():
            raise serializers.ValidationError({"due_date": "Due date must be in the future."})
        return attrs


class BorrowTransactionReturnInputSerializer(serializers.Serializer):
    """Validates data for marking a book as returned."""

    return_date = serializers.DateField(help_text="Actual return date (YYYY-MM-DD).")

    def validate_return_date(self, value):
        from datetime import date

        if value > date.today():
            raise serializers.ValidationError("Return date cannot be in the future.")
        return value


# ---------------------------------------------------------------------------
# BorrowTransaction — Output
# ---------------------------------------------------------------------------


class BorrowTransactionOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a BorrowTransaction, with computed properties."""

    member = MemberProfileOutputSerializer(read_only=True)
    book_copy = BookCopyOutputSerializer(read_only=True)
    library = LibraryOutputSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    overdue_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = BorrowTransaction
        fields = [
            "id",
            "member",
            "book_copy",
            "library",
            "status",
            "borrow_date",
            "due_date",
            "return_date",
            "is_overdue",
            "overdue_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BorrowTransactionListOutputSerializer(serializers.ModelSerializer):
    """Lightweight output for list views — avoids deeply nested serializers."""

    member_name = serializers.CharField(source="member.user.name", read_only=True)
    book_title = serializers.CharField(source="book_copy.book.title", read_only=True)
    library_code = serializers.CharField(source="library.code", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    overdue_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = BorrowTransaction
        fields = [
            "id",
            "member_name",
            "book_title",
            "library_code",
            "status",
            "borrow_date",
            "due_date",
            "return_date",
            "is_overdue",
            "overdue_days",
        ]
        read_only_fields = fields
