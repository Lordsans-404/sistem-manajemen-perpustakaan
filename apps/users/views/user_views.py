import logging

from rest_framework import status
from rest_framework.views import APIView

from config.api_response import error_response, success_response

from apps.users.selectors import get_all_users, get_user_by_id
from apps.users.serializers import (
    UserOutputSerializer,
    UserRegisterInputSerializer,
    UserUpdateInputSerializer,
)
from apps.users.services import create_user, update_user

logger = logging.getLogger(__name__)


class UserRegisterView(APIView):
    """
    POST /api/v1/users/register/
    Register a new user account.
    """

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

    def get(self, request):
        user = get_user_by_id(request.user.pk)
        if not user:
            return error_response(message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return success_response(data=UserOutputSerializer(user).data)

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
            data=UserOutputSerializer(user).data,
            message="Profile updated successfully.",
        )
