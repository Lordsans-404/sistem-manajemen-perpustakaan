from apps.users.models import MemberProfile


def get_member_by_id(member_id):
    """Return a MemberProfile by primary key with user prefetched, or None."""
    return (
        MemberProfile.objects
        .select_related("user")
        .filter(pk=member_id)
        .first()
    )


def get_member_by_user_id(user_id):
    """Return a MemberProfile by its related user's PK, or None."""
    return (
        MemberProfile.objects
        .select_related("user")
        .filter(user_id=user_id)
        .first()
    )


def get_member_by_identity_number(identity_number: str):
    """Return a MemberProfile by identity number, or None."""
    return (
        MemberProfile.objects
        .select_related("user")
        .filter(identity_number=identity_number)
        .first()
    )


def get_all_members(verified_only: bool = False):
    """
    Return all member profiles with user relation pre-fetched.
    Pass verified_only=True to filter only verified members.
    """
    qs = MemberProfile.objects.select_related("user").order_by("user__name")
    if verified_only:
        qs = qs.exclude(verified_at=None)
    return qs


def get_members_by_type(member_type: str):
    """Return all members of a specific type (student, lecturer, etc.)."""
    return (
        MemberProfile.objects
        .select_related("user")
        .filter(member_type=member_type)
        .order_by("user__name")
    )
