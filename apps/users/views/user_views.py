import logging

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response 
from config.permissions import IsAdmin, IsStaff

from apps.users.selectors import get_user_by_id
from apps.users.serializers import ( 
    MemberProfileOutputSerializer,
    StaffProfileOutputSerializer,
    UserOutputSerializer,
    UserRegisterInputSerializer,
    UserUpdateInputSerializer,
)
from apps.users.services import activate_user, create_user, deactivate_user, update_user

logger = logging.getLogger(__name__)


class UserRegisterView(APIView):
    """
    POST /api/v1/users/register/
    Register a new user account.
    """

    authentication_classes = []   # skip JWT auth — user doesn't have a token yet
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegisterInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        try:
            user = create_user(
                name=data["name"],
                email=data["email"],
                password=data["password"],
                phone_number=data.get("phone_number") or None,
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        return success_response(
            data=UserOutputSerializer(user).data,
            message="User registered successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class UserMeView(APIView):
    """
    GET  /api/v1/users/me/   — retrieve own profile
    PATCH /api/v1/users/me/  — update own profile
    """

    permission_classes = [IsAuthenticated]

    def _build_profile_data(self, user):
        """
        Compose full profile response from multiple serializers.
        Attaches member_profile and staff_profile conditionally.
        Both default to null if the user has no linked profile.
        """
        data = dict(UserOutputSerializer(user).data)

        # Attach member profile — null if user has no member profile yet.
        try:
            data["member_profile"] = MemberProfileOutputSerializer(
                user.member_profile
            ).data
        except ObjectDoesNotExist:
            data["member_profile"] = None

        # Attach staff profile — null if user is not a staff member.
        try:
            data["staff_profile"] = StaffProfileOutputSerializer(
                user.staff_profile
            ).data
        except ObjectDoesNotExist:
            data["staff_profile"] = None

        return data

    def get(self, request):
        return success_response(data=self._build_profile_data(request.user))

    def patch(self, request):
        serializer = UserUpdateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        user = update_user(
            user=request.user,
            name=data.get("name"),
            phone_number=data.get("phone_number"),
        )
        return success_response(
            data=self._build_profile_data(user),
            message="Profile updated successfully.",
        )


class UserDeactivateView(APIView):
    """
    PATCH /api/v1/users/{id}/deactivate/
    Deactivate a user (admin or supervisor only).
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        user = get_user_by_id(pk)
        if not user:
            return error_response(
                message="User not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        user = deactivate_user(user=user)
        return success_response(
            data=UserOutputSerializer(user).data,
            message="User deactivated successfully.",
        )


class UserActivateView(APIView):
    """
    PATCH /api/v1/users/{id}/activate/
    Reactivate a user (admin or supervisor only).
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        user = get_user_by_id(pk)
        if not user:
            return error_response(
                message="User not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        user = activate_user(user=user)
        return success_response(
            data=UserOutputSerializer(user).data,
            message="User activated successfully.",
        )
