from rest_framework import serializers

from apps.users.models import MemberProfile
from apps.users.serializers.user_serializers import UserOutputSerializer


# ---------------------------------------------------------------------------
# MemberProfile — Input
# ---------------------------------------------------------------------------


class MemberProfileInputSerializer(serializers.Serializer):
    """Validates data for creating a MemberProfile (linked to an existing User)."""

    member_type = serializers.ChoiceField(choices=MemberProfile.MemberType.choices)
    identity_number = serializers.CharField(max_length=50)

    def validate_identity_number(self, value: str) -> str:
        qs = MemberProfile.objects.filter(identity_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This identity number is already registered.")
        return value


class MemberProfileUpdateInputSerializer(serializers.Serializer):
    """Validates data for a partial MemberProfile update (PATCH)."""

    member_type = serializers.ChoiceField(choices=MemberProfile.MemberType.choices, required=False)
    member_level = serializers.ChoiceField(choices=MemberProfile.MemberLevel.choices, required=False)


# ---------------------------------------------------------------------------
# MemberProfile — Output
# ---------------------------------------------------------------------------


class MemberProfileOutputSerializer(serializers.ModelSerializer):
    """Read-only representation of a MemberProfile, includes nested User."""

    user = UserOutputSerializer(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = MemberProfile
        fields = [
            "id",
            "user",
            "member_type",
            "identity_number",
            "member_level",
            "is_verified",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
