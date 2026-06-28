import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.serializers import CharField, EmailField, Serializer
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from apps.users.selectors import get_user_by_email
from apps.users.services import login_with_supabase

logger = logging.getLogger(__name__)


class LoginInputSerializer(Serializer):
    email = EmailField()
    password = CharField(min_length=8, write_only=True)


class LoginView(APIView):
    """
    POST /api/v1/users/login/
    Authenticates via Supabase Auth and returns JWT tokens.

    Permission: public — no authentication required.
    """

    authentication_classes = []   # skip JWT auth for this endpoint
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        
        user = get_user_by_email(data["email"])
        if user and not user.is_active:
            return error_response(
                message="This account has been deactivated.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            tokens = login_with_supabase(
                email=data["email"],
                password=data["password"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return success_response(
            data=tokens,
            message="Login successful.",
        )
