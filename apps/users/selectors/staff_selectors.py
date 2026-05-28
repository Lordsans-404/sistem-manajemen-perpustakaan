from apps.users.models import StaffProfile


def get_staff_by_id(staff_id):
    """Return a StaffProfile by primary key with user and library prefetched."""
    return (
        StaffProfile.objects
        .select_related("user", "library")
        .filter(pk=staff_id)
        .first()
    )


def get_staff_by_user_id(user_id):
    """Return a StaffProfile by its related user's PK, or None."""
    return (
        StaffProfile.objects
        .select_related("user", "library")
        .filter(user_id=user_id)
        .first()
    )


def get_all_staff():
    """Return all staff profiles with user and library relations pre-fetched."""
    return (
        StaffProfile.objects
        .select_related("user", "library")
        .order_by("user__name")
    )


def get_staff_by_library(library_id):
    """Return all staff members assigned to a specific library."""
    return (
        StaffProfile.objects
        .select_related("user", "library")
        .filter(library_id=library_id)
        .order_by("user__name")
    )


def get_staff_by_role(role: str):
    """Return all staff members with a specific role."""
    return (
        StaffProfile.objects
        .select_related("user", "library")
        .filter(role=role)
        .order_by("user__name")
    )
