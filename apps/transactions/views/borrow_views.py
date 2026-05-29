import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.permissions import IsMember, IsStaff

from apps.catalog.selectors import get_book_copy_by_id
from apps.transactions.selectors import (
    get_all_borrows,
    get_borrow_by_id,
)
from apps.transactions.serializers import (
    BorrowTransactionInputSerializer,
    BorrowTransactionListOutputSerializer,
    BorrowTransactionOutputSerializer,
    BorrowTransactionReturnInputSerializer,
)
from apps.transactions.services import create_borrow_transaction, return_book
from apps.users.selectors import get_library_by_id, get_member_by_id

logger = logging.getLogger(__name__)


class BorrowListView(APIView):
    """
    GET  /api/v1/transactions/borrows/   — list all borrows
         Supports query params:
           ?status=active    → unreturned only
           ?status=returned  → returned only
           ?status=overdue   → overdue only
    POST /api/v1/transactions/borrows/   — create a new borrow (borrow a book)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsMember()]

    def get(self, request):
        status_param = request.query_params.get("status")

        if status_param == "overdue":
            from apps.transactions.selectors import get_overdue_borrows
            borrows = get_overdue_borrows()
        elif status_param == "active":
            borrows = get_all_borrows(returned=False)
        elif status_param == "returned":
            borrows = get_all_borrows(returned=True)
        else:
            borrows = get_all_borrows()

        return success_response(
            data=BorrowTransactionListOutputSerializer(borrows, many=True).data
        )

    def post(self, request):
        serializer = BorrowTransactionInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data

        member = get_member_by_id(data["member_id"])
        if not member:
            return error_response(
                message="Member not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        book_copy = get_book_copy_by_id(data["book_copy_id"])
        if not book_copy:
            return error_response(
                message="Book copy not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        library = get_library_by_id(data["library_id"])
        if not library:
            return error_response(
                message="Library not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            borrow = create_borrow_transaction(
                member=member,
                book_copy=book_copy,
                library=library,
                due_date=data["due_date"],
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        # Fetch with full relations for output
        borrow = get_borrow_by_id(borrow.pk)
        return success_response(
            data=BorrowTransactionOutputSerializer(borrow).data,
            message="Book borrowed successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class BorrowDetailView(APIView):
    """
    GET  /api/v1/transactions/borrows/{id}/  — retrieve borrow detail
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        borrow = get_borrow_by_id(pk)
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=BorrowTransactionOutputSerializer(borrow).data)


class BorrowReturnView(APIView):
    """
    POST /api/v1/transactions/borrows/{id}/return/
    Mark a borrowed book as returned.
    Auto-creates an overdue fine if the book is returned late.
    """

    permission_classes = [IsStaff]

    def post(self, request, pk):
        borrow = get_borrow_by_id(pk)
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = BorrowTransactionReturnInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        try:
            borrow = return_book(
                borrow=borrow,
                return_date=data["return_date"],
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        # Refresh with full relations
        borrow = get_borrow_by_id(borrow.pk)
        was_overdue = borrow.return_date > borrow.due_date if borrow.return_date else False
        msg = "Book returned successfully."
        if was_overdue:
            msg += " An overdue fine has been automatically created."

        return success_response(
            data=BorrowTransactionOutputSerializer(borrow).data,
            message=msg,
        )
