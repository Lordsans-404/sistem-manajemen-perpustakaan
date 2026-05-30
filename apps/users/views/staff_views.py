import logging

from rest_framework import status
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsAdmin, IsStaff

from apps.users.selectors import (
    get_all_staff,
    get_library_by_id,
    get_staff_by_id,
    get_user_by_id,
)
from apps.users.serializers import (
    StaffProfileInputSerializer,
    StaffProfileOutputSerializer,
    StaffProfileUpdateInputSerializer,
)
from apps.users.services import create_staff_profile, update_staff_profile

logger = logging.getLogger(__name__)


class StaffListView(APIView):
    """
    GET  /api/v1/users/staff/  — list all staff
    POST /api/v1/users/staff/  — create a staff profile for a user
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsStaff()]
        return [IsAdmin()]

    def get(self, request):
        staff = get_all_staff()
        paginator = StandardPagination()
        page = paginator.paginate_queryset(staff, request)
        return paginator.get_paginated_response(
            StaffProfileOutputSerializer(page, many=True).data
        )

    def post(self, request):
        # Expect user_id in the body to link the profile
        user_id = request.data.get("user_id")
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

        serializer = StaffProfileInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        library = get_library_by_id(data["library_id"])
        if not library:
            return error_response(
                message="Library not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            profile = create_staff_profile(
                user=user,
                library=library,
                role=data["role"],
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        return success_response(
            data=StaffProfileOutputSerializer(profile).data,
            message="Staff profile created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class StaffDetailView(APIView):
    """
    GET   /api/v1/users/staff/{id}/  — retrieve staff detail
    PATCH /api/v1/users/staff/{id}/  — update staff (library/role)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsStaff()]
        return [IsAdmin()]

    def _get_staff_or_404(self, staff_id):
        staff = get_staff_by_id(staff_id)
        if not staff:
            return None, error_response(
                message="Staff profile not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return staff, None

    def get(self, request, pk):
        staff, err = self._get_staff_or_404(pk)
        if err:
            return err
        return success_response(data=StaffProfileOutputSerializer(staff).data)

    def patch(self, request, pk):
        staff, err = self._get_staff_or_404(pk)
        if err:
            return err

        serializer = StaffProfileUpdateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        library = None
        if "library_id" in data:
            library = get_library_by_id(data["library_id"])
            if not library:
                return error_response(
                    message="Library not found.",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        staff = update_staff_profile(
            profile=staff,
            library=library,
            role=data.get("role"),
        )
        return success_response(
            data=StaffProfileOutputSerializer(staff).data,
            message="Staff profile updated successfully.",
        )
