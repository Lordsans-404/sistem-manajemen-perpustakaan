from rest_framework.permissions import BasePermission


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
        except AttributeError:
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
        except AttributeError:
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
        except AttributeError:
            return False
