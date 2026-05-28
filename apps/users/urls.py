from django.urls import path

# Views will be imported and registered here as they are implemented.
# Convention: /api/v1/users/...
#
# Planned endpoints:
#   POST   /api/v1/users/register/          — create new user account
#   GET    /api/v1/users/me/                — retrieve current user profile
#   PATCH  /api/v1/users/me/                — update current user profile
#
#   GET    /api/v1/users/libraries/         — list libraries
#   POST   /api/v1/users/libraries/         — create library
#   GET    /api/v1/users/libraries/{id}/    — retrieve library
#   PATCH  /api/v1/users/libraries/{id}/    — update library
#   DELETE /api/v1/users/libraries/{id}/    — delete library
#
#   GET    /api/v1/users/members/           — list members
#   POST   /api/v1/users/members/           — create member profile
#   GET    /api/v1/users/members/{id}/      — retrieve member
#   PATCH  /api/v1/users/members/{id}/      — update member
#   POST   /api/v1/users/members/{id}/verify/ — verify member
#
#   GET    /api/v1/users/staff/             — list staff
#   POST   /api/v1/users/staff/             — create staff profile
#   GET    /api/v1/users/staff/{id}/        — retrieve staff
#   PATCH  /api/v1/users/staff/{id}/        — update staff

app_name = "users"

urlpatterns = [
    # Endpoints will be registered here as views are implemented.
]
