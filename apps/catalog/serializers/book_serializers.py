from rest_framework import serializers

from apps.catalog.models import Book


# ---------------------------------------------------------------------------
# Book — Input
# ---------------------------------------------------------------------------


class BookInputSerializer(serializers.Serializer):
    """Validates data required to create or fully update a Book record."""

    title = serializers.CharField(max_length=500)
    author = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=100)


class BookUpdateInputSerializer(serializers.Serializer):
    """Validates data for a partial Book update (PATCH)."""

    title = serializers.CharField(max_length=500, required=False)
    author = serializers.CharField(max_length=255, required=False)
    category = serializers.CharField(max_length=100, required=False)


# ---------------------------------------------------------------------------
# Book — Output
# ---------------------------------------------------------------------------


class BookOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a Book title."""

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
