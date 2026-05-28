import logging

from django.db import transaction
from django.utils import timezone

from apps.users.models import MemberProfile, User

logger = logging.getLogger(__name__)


def create_member_profile(
    *,
    user: User,
    member_type: str,
    identity_number: str,
    member_level: str = MemberProfile.MemberLevel.BRONZE,
) -> MemberProfile:
    """
    Create a MemberProfile for an existing User.
    Raises ValueError if the user already has a profile or if
    identity_number is already taken.
    """
    if MemberProfile.objects.filter(user=user).exists():
        raise ValueError(f"User '{user.email}' already has a member profile.")

    identity_number = identity_number.strip()
    if MemberProfile.objects.filter(identity_number=identity_number).exists():
        raise ValueError(f"Identity number '{identity_number}' is already in use.")

    with transaction.atomic():
        profile = MemberProfile.objects.create(
            user=user,
            member_type=member_type,
            identity_number=identity_number,
            member_level=member_level,
        )

    logger.info(
        "member_profile.created profile_id=%s user_id=%s identity_number=%s",
        profile.pk, user.pk, identity_number,
    )
    return profile


def update_member_profile(
    *,
    profile: MemberProfile,
    member_type: str | None = None,
    member_level: str | None = None,
) -> MemberProfile:
    """Partially update a MemberProfile's non-identity fields."""
    updated_fields = []

    if member_type is not None:
        profile.member_type = member_type
        updated_fields.append("member_type")

    if member_level is not None:
        profile.member_level = member_level
        updated_fields.append("member_level")

    if updated_fields:
        profile.save(update_fields=updated_fields + ["updated_at"])
        logger.info("member_profile.updated profile_id=%s fields=%s", profile.pk, updated_fields)

    return profile


def verify_member(*, profile: MemberProfile) -> MemberProfile:
    """
    Mark a member as verified by setting verified_at to now.
    Idempotent — if already verified, returns the profile unchanged.
    """
    if profile.is_verified:
        logger.info("member_profile.already_verified profile_id=%s", profile.pk)
        return profile

    profile.verified_at = timezone.now()
    profile.save(update_fields=["verified_at", "updated_at"])
    logger.info("member_profile.verified profile_id=%s", profile.pk)
    return profile
