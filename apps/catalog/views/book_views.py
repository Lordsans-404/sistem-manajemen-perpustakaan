import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsStaff

from apps.catalog.selectors import get_all_books, get_book_by_id, search_books
from apps.catalog.serializers import (
    BookInputSerializer,
    BookOutputSerializer,
    BookUpdateInputSerializer,
)
from apps.catalog.services import create_book, delete_book, update_book

logger = logging.getLogger(__name__)


class BookListView(APIView):
    """
    GET  /api/v1/catalog/books/           — list all books (supports ?search=)
    POST /api/v1/catalog/books/           — create a new book
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsStaff()]

    def get(self, request):
        query = request.query_params.get("search", "").strip()
        books = search_books(query) if query else get_all_books()
        paginator = StandardPagination()
        page = paginator.paginate_queryset(books, request)
        return paginator.get_paginated_response(
            BookOutputSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = BookInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        book = create_book(
            title=data["title"],
            author=data["author"],
            category=data["category"],
        )
        return success_response(
            data=BookOutputSerializer(book).data,
            message="Book created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class BookDetailView(APIView):
    """
    GET    /api/v1/catalog/books/{id}/  — retrieve book detail
    PATCH  /api/v1/catalog/books/{id}/  — update book
    DELETE /api/v1/catalog/books/{id}/  — delete book
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsStaff()]

    def _get_book_or_404(self, book_id):
        book = get_book_by_id(book_id)
        if not book:
            return None, error_response(
                message="Book not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return book, None

    def get(self, request, pk):
        book, err = self._get_book_or_404(pk)
        if err:
            return err
        return success_response(data=BookOutputSerializer(book).data)

    def patch(self, request, pk):
        book, err = self._get_book_or_404(pk)
        if err:
            return err

        serializer = BookUpdateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        book = update_book(
            book=book,
            title=data.get("title"),
            author=data.get("author"),
            category=data.get("category"),
        )
        return success_response(
            data=BookOutputSerializer(book).data,
            message="Book updated successfully.",
        )

    def delete(self, request, pk):
        book, err = self._get_book_or_404(pk)
        if err:
            return err

        delete_book(book=book)
        return success_response(
            message="Book deleted successfully.",
            status_code=status.HTTP_204_NO_CONTENT,
        )
