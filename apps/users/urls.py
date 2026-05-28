from django.urls import path

from apps.users.views import (
    LibraryDetailView,
    LibraryListView,
    MemberDetailView,
    MemberListView,
    MemberVerifyView,
    StaffDetailView,
    StaffListView,
    UserMeView,
    UserRegisterView,
)

app_name = "users"

urlpatterns = [
    # --- User ---
    path("register/", UserRegisterView.as_view(), name="user-register"),
    path("me/", UserMeView.as_view(), name="user-me"),

    # --- Library ---
    path("libraries/", LibraryListView.as_view(), name="library-list"),
    path("libraries/<uuid:pk>/", LibraryDetailView.as_view(), name="library-detail"),

    # --- Member ---
    path("members/", MemberListView.as_view(), name="member-list"),
    path("members/<uuid:pk>/", MemberDetailView.as_view(), name="member-detail"),
    path("members/<uuid:pk>/verify/", MemberVerifyView.as_view(), name="member-verify"),

    # --- Staff ---
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path("staff/<uuid:pk>/", StaffDetailView.as_view(), name="staff-detail"),
]
