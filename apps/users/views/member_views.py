import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsStaff, can_access_member, get_request_member, is_staff_user

from apps.users.models import MemberProfile
from apps.users.selectors import (
    get_all_members,
    get_member_by_id,
    get_user_by_id,
)
from apps.users.serializers import (
    MemberProfileInputSerializer,
    MemberProfileOutputSerializer,
    MemberProfileUpdateInputSerializer,
)
from apps.users.services import create_member_profile, update_member_profile, verify_member
from django.conf import settings

logger = logging.getLogger(__name__)


class MemberListView(APIView):
    """
    GET  /api/v1/users/members/  — list all members
    POST /api/v1/users/members/  — create a member profile for a user
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        if self.request.method == "POST":
            # Feature flag — self-register for development
            if getattr(settings, "ALLOW_SELF_MEMBER_REGISTRATION", False):
                return [IsAuthenticated()]
        return [IsStaff()]

    def get(self, request):
        verified_only = request.query_params.get("verified") == "true"

        if is_staff_user(request.user):
            # Staff sees all members.
            members = get_all_members(verified_only=verified_only)
        else:
            # Regular authenticated users see only their own member profile.
            own = get_request_member(request.user)
            if own is None:
                return error_response(
                    message="No member profile found for the current user.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            # Wrap as a queryset so pagination still works uniformly.
            members = MemberProfile.objects.filter(pk=own.pk)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(members, request)
        return paginator.get_paginated_response(
            MemberProfileOutputSerializer(page, many=True).data
        )

    def post(self, request):
        # For development allow self member registration temporarily
        user_id = request.data.get("user_id")
        if (
            getattr(settings, "ALLOW_SELF_MEMBER_REGISTRATION", False)
            and not is_staff_user(request.user)
        ):
            user_id = str(request.user.pk)

        if not user_id:
            return error_response(
                message="user_id is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = get_user_by_id(user_id)
        if not user:
            return error_response(
                message="User not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = MemberProfileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        try:
            profile = create_member_profile(
                user=user,
                member_type=data["member_type"],
                identity_number=data["identity_number"],
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        return success_response(
            data=MemberProfileOutputSerializer(profile).data,
            message="Member profile created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class MemberDetailView(APIView):
    """
    GET   /api/v1/users/members/{id}/  — retrieve member detail
    PATCH /api/v1/users/members/{id}/  — update member
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsStaff()]

    def _get_member_or_404(self, member_id):
        member = get_member_by_id(member_id)
        if not member:
            return None, error_response(
                message="Member profile not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return member, None

    def get(self, request, pk):
        member, err = self._get_member_or_404(pk)
        if err:
            return err

        if not can_access_member(request.user, member):
            return error_response(
                message="You do not have permission to view this member profile.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return success_response(data=MemberProfileOutputSerializer(member).data)

    def patch(self, request, pk):
        member, err = self._get_member_or_404(pk)
        if err:
            return err

        serializer = MemberProfileUpdateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        member = update_member_profile(
            profile=member,
            member_type=data.get("member_type"),
            member_level=data.get("member_level"),
        )
        return success_response(
            data=MemberProfileOutputSerializer(member).data,
            message="Member profile updated successfully.",
        )


class MemberVerifyView(APIView):
    """
    POST /api/v1/users/members/{id}/verify/
    Verify a member (staff action).
    """

    permission_classes = [IsStaff]

    def post(self, request, pk):
        member = get_member_by_id(pk)
        if not member:
            return error_response(
                message="Member profile not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        member = verify_member(profile=member)
        return success_response(
            data=MemberProfileOutputSerializer(member).data,
            message="Member verified successfully.",
        )
