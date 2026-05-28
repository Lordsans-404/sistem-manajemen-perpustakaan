import logging

from rest_framework import status
from rest_framework.views import APIView

from config.api_response import error_response, success_response

from apps.users.selectors import (
    get_all_libraries,
    get_library_by_id,
)
from apps.users.serializers import (
    LibraryInputSerializer,
    LibraryOutputSerializer,
)
from apps.users.services import create_library, delete_library, update_library

logger = logging.getLogger(__name__)


class LibraryListView(APIView):
    """
    GET  /api/v1/users/libraries/  — list all libraries
    POST /api/v1/users/libraries/  — create a new library
    """

    def get(self, request):
        libraries = get_all_libraries()
        return success_response(
            data=LibraryOutputSerializer(libraries, many=True).data
        )

    def post(self, request):
        serializer = LibraryInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        try:
            library = create_library(
                name=data["name"],
                type=data["type"],
                code=data["code"],
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        return success_response(
            data=LibraryOutputSerializer(library).data,
            message="Library created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class LibraryDetailView(APIView):
    """
    GET    /api/v1/users/libraries/{id}/  — retrieve library detail
    PATCH  /api/v1/users/libraries/{id}/  — update library
    DELETE /api/v1/users/libraries/{id}/  — delete library
    """

    def _get_library_or_404(self, library_id):
        library = get_library_by_id(library_id)
        if not library:
            return None, error_response(
                message="Library not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return library, None

    def get(self, request, pk):
        library, err = self._get_library_or_404(pk)
        if err:
            return err
        return success_response(data=LibraryOutputSerializer(library).data)

    def patch(self, request, pk):
        library, err = self._get_library_or_404(pk)
        if err:
            return err

        # Pass instance for uniqueness-exclude in serializer
        serializer = LibraryInputSerializer(instance=library, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        try:
            library = update_library(
                library=library,
                name=data.get("name"),
                type=data.get("type"),
                code=data.get("code"),
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        return success_response(
            data=LibraryOutputSerializer(library).data,
            message="Library updated successfully.",
        )

    def delete(self, request, pk):
        library, err = self._get_library_or_404(pk)
        if err:
            return err

        try:
            delete_library(library=library)
        except Exception as exc:
            return error_response(
                message="Cannot delete library. It may have staff or book copies referencing it.",
                status_code=status.HTTP_409_CONFLICT,
            )

        return success_response(
            message="Library deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT,
        )
