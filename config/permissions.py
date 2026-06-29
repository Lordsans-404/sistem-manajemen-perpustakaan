from rest_framework.permissions import BasePermission
from django.core.exceptions import ObjectDoesNotExist


# ---------------------------------------------------------------------------
# Access helper functions
# ---------------------------------------------------------------------------

def is_staff_user(user) -> bool:
    """Return True if *user* has a staff_profile (any role)."""
    try:
        _ = user.staff_profile
        return True
    except ObjectDoesNotExist:
        return False


def is_admin_user(user) -> bool:
    """
    Return True if *user* is an admin or supervisor.
    These roles have unrestricted access across all library branches.
    Librarians are scoped to their assigned library.
    """
    try:
        return user.staff_profile.role in {"admin", "supervisor"}
    except ObjectDoesNotExist:
        return False


def get_staff_library(user):
    """
    Return the Library assigned to the staff user's profile, or None.
    Used to enforce library-scoped access for non-admin staff.
    """
    try:
        return user.staff_profile.library
    except ObjectDoesNotExist:
        return None


def get_request_member(user):
    """
    Return the MemberProfile linked to *user*, or None if the user has no
    member profile.  Views should return 403 when this returns None and the
    endpoint is member-only.
    """
    try:
        return user.member_profile
    except ObjectDoesNotExist:
        return None


def can_access_member(user, member) -> bool:
    """
    Return True if *user* is staff OR is the same person as *member*.
    Used for detail endpoints where staff sees any record but a member only
    sees their own.
    """
    if is_staff_user(user):
        return True
    try:
        return user.member_profile.pk == member.pk
    except ObjectDoesNotExist:
        return False


class IsMember(BasePermission):
    """
    Allows access only to verified library members.

    Conditions:
    - User must be authenticated.
    - User must have a MemberProfile linked.
    - MemberProfile.is_verified must be True (verified_at is not None).
    """

    message = "Access denied. You must be a verified library member."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.member_profile.is_verified
        except ObjectDoesNotExist:
            return False


class IsStaff(BasePermission):
    """
    Allows access only to library staff (librarian, admin, supervisor).

    Conditions:
    - User must be authenticated.
    - User must have a StaffProfile linked (any role).
    """

    message = "Access denied. You must be a library staff member."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            # Accessing staff_profile raises RelatedObjectDoesNotExist if absent
            _ = request.user.staff_profile
            return True
        except ObjectDoesNotExist:
            return False


class IsAdmin(BasePermission):
    """
    Allows access only to library admins and supervisors.

    Conditions:
    - User must be authenticated.
    - User must have a StaffProfile with role 'admin' or 'supervisor'.
    """

    message = "Access denied. You must be a library admin or supervisor."

    ADMIN_ROLES = {"admin", "supervisor"}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.staff_profile.role in self.ADMIN_ROLES
        except ObjectDoesNotExist:
            return False


class IsMemberOrStaff(BasePermission):
    """
    Allows access to verified library members OR any staff.

    Conditions (OR):
    - User has a StaffProfile (any role), OR
    - User has a verified MemberProfile (verified_at is not None).

    Used for endpoints like POST /borrows/ where both staff and verified
    members should have access, but plain authenticated users (no profile)
    should be rejected.
    """

    message = "Access denied. You must be a verified member or a library staff member."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check staff first (faster, more common path for mutations)
        try:
            _ = request.user.staff_profile
            return True
        except ObjectDoesNotExist:
            pass
        # Fallback: check if verified member
        try:
            return request.user.member_profile.is_verified
        except ObjectDoesNotExist:
            return False
