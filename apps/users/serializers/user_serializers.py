from rest_framework import serializers

from apps.users.models import User


# ---------------------------------------------------------------------------
# User — Input
# ---------------------------------------------------------------------------


class UserRegisterInputSerializer(serializers.Serializer):
    """Validates data required to register a new user account."""

    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()


class UserUpdateInputSerializer(serializers.Serializer):
    """Validates data for a partial user profile update (PATCH)."""

    name = serializers.CharField(max_length=255, required=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)


# ---------------------------------------------------------------------------
# User — Output
# ---------------------------------------------------------------------------


class UserOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a User, safe to expose via API."""

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
