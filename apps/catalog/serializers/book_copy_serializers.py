from rest_framework import serializers

from apps.catalog.models import BookCopy
from apps.catalog.serializers.book_serializers import BookOutputSerializer
from apps.users.serializers.library_serializers import LibraryOutputSerializer


# ---------------------------------------------------------------------------
# BookCopy — Input
# ---------------------------------------------------------------------------


class BookCopyInputSerializer(serializers.Serializer):
    """Validates data required to create a new physical BookCopy."""

    book_id = serializers.UUIDField(help_text="UUID of the parent Book record.")
    library_id = serializers.UUIDField(help_text="UUID of the Library that holds this copy.")
    condition = serializers.ChoiceField(choices=BookCopy.Condition.choices)
    isbn = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    publisher = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    publication_year = serializers.IntegerField(
        min_value=1000,
        max_value=9999,
        required=False,
        allow_null=True,
    )


class BookCopyUpdateInputSerializer(serializers.Serializer):
    """Validates data for a partial BookCopy update (PATCH)."""

    condition = serializers.ChoiceField(choices=BookCopy.Condition.choices, required=False)
    isbn = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    publisher = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    publication_year = serializers.IntegerField(
        min_value=1000,
        max_value=9999,
        required=False,
        allow_null=True,
    )


# ---------------------------------------------------------------------------
# BookCopy — Output
# ---------------------------------------------------------------------------


class BookCopyOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a physical BookCopy, includes nested Book and Library."""

    book = BookOutputSerializer(read_only=True)
    library = LibraryOutputSerializer(read_only=True)

    class Meta:
        model = BookCopy
        fields = [
            "id",
            "book",
            "library",
            "condition",
            "isbn",
            "publisher",
            "publication_year",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
