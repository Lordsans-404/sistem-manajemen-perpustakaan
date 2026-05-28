# serializers package — validation & transformation
#
# Exports:
#   users:
#     UserRegisterInputSerializer, UserUpdateInputSerializer, UserOutputSerializer
#   library:
#     LibraryInputSerializer, LibraryOutputSerializer
#   member:
#     MemberProfileInputSerializer, MemberProfileUpdateInputSerializer, MemberProfileOutputSerializer
#   staff:
#     StaffProfileInputSerializer, StaffProfileUpdateInputSerializer, StaffProfileOutputSerializer

from apps.users.serializers.user_serializers import (
    UserOutputSerializer,
    UserRegisterInputSerializer,
    UserUpdateInputSerializer,
)
from apps.users.serializers.library_serializers import (
    LibraryInputSerializer,
    LibraryOutputSerializer,
)
from apps.users.serializers.member_serializers import (
    MemberProfileInputSerializer,
    MemberProfileOutputSerializer,
    MemberProfileUpdateInputSerializer,
)
from apps.users.serializers.staff_serializers import (
    StaffProfileInputSerializer,
    StaffProfileOutputSerializer,
    StaffProfileUpdateInputSerializer,
)

__all__ = [
    # User
    "UserRegisterInputSerializer",
    "UserUpdateInputSerializer",
    "UserOutputSerializer",
    # Library
    "LibraryInputSerializer",
    "LibraryOutputSerializer",
    # MemberProfile
    "MemberProfileInputSerializer",
    "MemberProfileUpdateInputSerializer",
    "MemberProfileOutputSerializer",
    # StaffProfile
    "StaffProfileInputSerializer",
    "StaffProfileUpdateInputSerializer",
    "StaffProfileOutputSerializer",
]
