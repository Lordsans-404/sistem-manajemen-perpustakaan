import logging
from datetime import date

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsMember, IsStaff, get_request_member, is_staff_user

from apps.catalog.selectors import get_book_copy_by_id
from apps.transactions.selectors import (
    get_all_borrows,
    get_borrow_by_id,
    get_borrows_by_member,
    get_overdue_borrows,
)
from apps.transactions.serializers import (
    BorrowTransactionInputSerializer,
    BorrowTransactionListOutputSerializer,
    BorrowTransactionOutputSerializer,
    BorrowTransactionReturnInputSerializer,
)
from apps.transactions.services import (
    approve_borrow,
    create_borrow_transaction,
    reject_borrow,
    return_book,
    update_borrow_status,
)
from apps.users.selectors import get_library_by_id, get_member_by_id

logger = logging.getLogger(__name__)


class BorrowListView(APIView):
    """
    GET  /api/v1/transactions/borrows/   — list all borrows
    POST /api/v1/transactions/borrows/   — create a new borrow (borrow a book)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        # POST
        return [IsMember() | IsStaff()]

    def get(self, request):
        status_param = request.query_params.get("status")

        if is_staff_user(request.user):
            if status_param == "overdue":
                borrows = get_overdue_borrows()
            elif status_param in ["pending", "active", "returned", "failed"]:
                borrows = get_all_borrows(status=status_param)
            else:
                borrows = get_all_borrows()
        else:
            member = get_request_member(request.user)
            if member is None:
                return error_response(
                    message="No member profile found for the current user.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            if status_param == "overdue":
                borrows = get_borrows_by_member(
                    member.pk, status="active"
                ).filter(due_date__lt=date.today())
            elif status_param in ["pending", "active", "returned", "failed"]:
                borrows = get_borrows_by_member(member.pk, status=status_param)
            else:
                borrows = get_borrows_by_member(member.pk)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(borrows, request)
        return paginator.get_paginated_response(
            BorrowTransactionListOutputSerializer(page, many=True).data
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

        # Check if member is verified (if borrowing for themselves)
        if not member.is_verified:
            return error_response(
                message="Member account is not verified. Please contact library staff.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Non-staff members can only borrow on behalf of themselves.
        if not is_staff_user(request.user):
            own = get_request_member(request.user)
            if own is None or own.pk != member.pk:
                return error_response(
                    message="You can only create borrows for your own member account.",
                    status_code=status.HTTP_403_FORBIDDEN,
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
            message="Borrow request submitted and is pending staff approval.",
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

        # Non-staff may only view their own borrow records.
        if not is_staff_user(request.user):
            own = get_request_member(request.user)
            if own is None or borrow.member_id != own.pk:
                return error_response(
                    message="You do not have permission to view this borrow transaction.",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        return success_response(data=BorrowTransactionOutputSerializer(borrow).data)

    def patch(self, request, pk):
        if not is_staff_user(request.user):
            return error_response(
                message="Only staff can update borrow transactions manually.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        borrow = get_borrow_by_id(pk)
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        new_status = request.data.get("status")
        if not new_status:
            return error_response(
                message="status field is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            borrow = update_borrow_status(borrow=borrow, new_status=new_status)
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        borrow = get_borrow_by_id(borrow.pk)
        return success_response(
            data=BorrowTransactionOutputSerializer(borrow).data,
            message="Borrow status updated successfully.",
        )


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


class BorrowApproveView(APIView):
    """
    POST /api/v1/transactions/borrows/{id}/approve/
    Approve a pending borrow request.
    """

    permission_classes = [IsStaff]

    def post(self, request, pk):
        borrow = get_borrow_by_id(pk)
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            borrow = approve_borrow(borrow=borrow)
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        borrow = get_borrow_by_id(borrow.pk)
        return success_response(
            data=BorrowTransactionOutputSerializer(borrow).data,
            message="Borrow request approved successfully.",
        )


class BorrowRejectView(APIView):
    """
    POST /api/v1/transactions/borrows/{id}/reject/
    Reject a pending borrow request.
    """

    permission_classes = [IsStaff]

    def post(self, request, pk):
        borrow = get_borrow_by_id(pk)
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            borrow = reject_borrow(borrow=borrow)
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        borrow = get_borrow_by_id(borrow.pk)
        return success_response(
            data=BorrowTransactionOutputSerializer(borrow).data,
            message="Borrow request rejected successfully.",
        )
