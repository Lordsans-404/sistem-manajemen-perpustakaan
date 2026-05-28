from apps.users.views.user_views import UserMeView, UserRegisterView
from apps.users.views.library_views import LibraryDetailView, LibraryListView
from apps.users.views.member_views import MemberDetailView, MemberListView, MemberVerifyView
from apps.users.views.staff_views import StaffDetailView, StaffListView

__all__ = [
    # user
    "UserRegisterView",
    "UserMeView",
    # library
    "LibraryListView",
    "LibraryDetailView",
    # member
    "MemberListView",
    "MemberDetailView",
    "MemberVerifyView",
    # staff
    "StaffListView",
    "StaffDetailView",
]
