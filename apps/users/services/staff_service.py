import logging

from django.db import transaction

from apps.users.models import Library, StaffProfile, User

logger = logging.getLogger(__name__)


def create_staff_profile(
    *,
    user: User,
    library: Library,
    role: str = StaffProfile.StaffRole.LIBRARIAN,
) -> StaffProfile:
    """
    Create a StaffProfile for an existing User.
    Raises ValueError if the user already has a staff profile.
    """
    if StaffProfile.objects.filter(user=user).exists():
        raise ValueError(f"User '{user.email}' already has a staff profile.")

    with transaction.atomic():
        profile = StaffProfile.objects.create(
            user=user,
            library=library,
            role=role,
        )
        # Elevate Django's is_staff flag so staff can access the admin panel
        if not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff", "updated_at"])

    logger.info(
        "staff_profile.created profile_id=%s user_id=%s library=%s role=%s",
        profile.pk, user.pk, library.code, role,
    )
    return profile


def update_staff_profile(
    *,
    profile: StaffProfile,
    library: Library | None = None,
    role: str | None = None,
) -> StaffProfile:
    """Partially update a StaffProfile (reassign library or change role)."""
    updated_fields = []

    if library is not None:
        profile.library = library
        updated_fields.append("library")

    if role is not None:
        profile.role = role
        updated_fields.append("role")

    if updated_fields:
        profile.save(update_fields=updated_fields + ["updated_at"])
        logger.info("staff_profile.updated profile_id=%s fields=%s", profile.pk, updated_fields)

    return profile
