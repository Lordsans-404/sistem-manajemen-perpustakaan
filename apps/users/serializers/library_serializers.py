from rest_framework import serializers

from apps.users.models import Library


# ---------------------------------------------------------------------------
# Library — Input
# ---------------------------------------------------------------------------


class LibraryInputSerializer(serializers.Serializer):
    """Validates data required to create or update a Library branch."""

    name = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=Library.LibraryType.choices)
    code = serializers.CharField(max_length=50)

    def validate_code(self, value: str) -> str:
        """Ensure the library code is uppercase and unique (on create)."""
        value = value.upper()
        qs = Library.objects.filter(code=value)
        # On update, exclude the current instance from uniqueness check.
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Library with code '{value}' already exists.")
        return value


# ---------------------------------------------------------------------------
# Library — Output
# ---------------------------------------------------------------------------


class LibraryOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a Library branch."""

    class Meta:
        model = Library
        fields = [
            "id",
            "name",
            "type",
            "code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
