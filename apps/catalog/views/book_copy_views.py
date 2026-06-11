import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsStaff

from apps.catalog.selectors import (
    get_all_book_copies,
    get_book_by_id,
    get_book_copy_by_id,
)
from apps.catalog.serializers import (
    BookCopyInputSerializer,
    BookCopyOutputSerializer,
    BookCopyUpdateInputSerializer,
)
from apps.catalog.services import create_book_copy, delete_book_copy, update_book_copy
from apps.users.selectors import get_library_by_id

logger = logging.getLogger(__name__)


class BookCopyListView(APIView):
    """
    GET  /api/v1/catalog/book-copies/  — list all book copies (supports ?book_id= ?library_id=)
    POST /api/v1/catalog/book-copies/  — create a new book copy
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsStaff()]

    def get(self, request):
        book_id = request.query_params.get("book_id")
        library_id = request.query_params.get("library_id")
        available_param = request.query_params.get("available")

        if available_param == "true":
            qs = get_available_copies(book_id=book_id, library_id=library_id)
        else:
            qs = get_all_book_copies()
            if book_id:
                qs = qs.filter(book_id=book_id)
            if library_id:
                qs = qs.filter(library_id=library_id)
            
            if available_param == "false":
                qs = qs.filter(borrow_transactions__return_date__isnull=True)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            BookCopyOutputSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = BookCopyInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data

        book = get_book_by_id(data["book_id"])
        if not book:
            return error_response(
                message="Book not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        library = get_library_by_id(data["library_id"])
        if not library:
            return error_response(
                message="Library not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        copy = create_book_copy(
            book=book,
            library=library,
            condition=data["condition"],
            isbn=data.get("isbn"),
            publisher=data.get("publisher"),
            publication_year=data.get("publication_year"),
        )
        return success_response(
            data=BookCopyOutputSerializer(copy).data,
            message="Book copy created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class BookCopyDetailView(APIView):
    """
    GET    /api/v1/catalog/book-copies/{id}/  — retrieve copy detail
    PATCH  /api/v1/catalog/book-copies/{id}/  — update copy condition/metadata
    DELETE /api/v1/catalog/book-copies/{id}/  — delete copy
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsStaff()]

    def _get_copy_or_404(self, copy_id):
        copy = get_book_copy_by_id(copy_id)
        if not copy:
            return None, error_response(
                message="Book copy not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return copy, None

    def get(self, request, pk):
        copy, err = self._get_copy_or_404(pk)
        if err:
            return err
        return success_response(data=BookCopyOutputSerializer(copy).data)

    def patch(self, request, pk):
        copy, err = self._get_copy_or_404(pk)
        if err:
            return err

        serializer = BookCopyUpdateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        copy = update_book_copy(
            copy=copy,
            condition=data.get("condition"),
            isbn=data.get("isbn"),
            publisher=data.get("publisher"),
            publication_year=data.get("publication_year"),
        )
        return success_response(
            data=BookCopyOutputSerializer(copy).data,
            message="Book copy updated successfully.",
        )

    def delete(self, request, pk):
        copy, err = self._get_copy_or_404(pk)
        if err:
            return err

        try:
            delete_book_copy(copy=copy)
        except Exception:
            return error_response(
                message="Cannot delete book copy. It may have an active borrow transaction.",
                status_code=status.HTTP_409_CONFLICT,
            )

        return success_response(
            message="Book copy deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT,
        )
