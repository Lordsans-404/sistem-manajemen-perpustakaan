from rest_framework import serializers

from apps.users.models import StaffProfile
from apps.users.serializers.library_serializers import LibraryOutputSerializer
from apps.users.serializers.user_serializers import UserOutputSerializer


# ---------------------------------------------------------------------------
# StaffProfile — Input
# ---------------------------------------------------------------------------


class StaffProfileInputSerializer(serializers.Serializer):
    """Validates data for creating a StaffProfile."""

    library_id = serializers.UUIDField(
        help_text="UUID of the Library branch this staff member is assigned to."
    )
    role = serializers.ChoiceField(choices=StaffProfile.StaffRole.choices)


class StaffProfileUpdateInputSerializer(serializers.Serializer):
    """Validates data for a partial StaffProfile update (PATCH)."""

    library_id = serializers.UUIDField(required=False)
    role = serializers.ChoiceField(choices=StaffProfile.StaffRole.choices, required=False)


# ---------------------------------------------------------------------------
# StaffProfile — Output
# ---------------------------------------------------------------------------


class StaffProfileOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a StaffProfile, includes nested User and Library."""

    user = UserOutputSerializer(read_only=True)
    library = LibraryOutputSerializer(read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            "id",
            "user",
            "library",
            "role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
