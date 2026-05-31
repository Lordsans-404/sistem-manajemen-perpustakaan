import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from config.api_response import error_response, success_response
from config.pagination import StandardPagination
from config.permissions import IsAdmin, IsStaff

from apps.transactions.selectors import get_all_fines, get_borrow_by_id, get_fine_by_id
from apps.transactions.serializers import (
    FineInputSerializer,
    FineOutputSerializer,
    FinePaymentInputSerializer,
)
from apps.transactions.services import create_manual_fine, pay_fine, waive_fine

logger = logging.getLogger(__name__)


class FineListView(APIView):
    """
    GET  /api/v1/transactions/fines/   — list all fines
         Supports ?payment_status=unpaid|paid|waived
    POST /api/v1/transactions/fines/   — create a manual fine (staff: damage/loss/other)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsStaff()]

    def get(self, request):
        payment_status = request.query_params.get("payment_status")
        fines = get_all_fines(payment_status=payment_status)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(fines, request)
        return paginator.get_paginated_response(
            FineOutputSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = FineInputSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        data = serializer.validated_data
        borrow = get_borrow_by_id(data["borrow_transaction_id"])
        if not borrow:
            return error_response(
                message="Borrow transaction not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            fine = create_manual_fine(
                borrow=borrow,
                fine_type=data["fine_type"],
                amount=data["amount"],
                description=data.get("description", ""),
            )
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        fine = get_fine_by_id(fine.pk)
        return success_response(
            data=FineOutputSerializer(fine).data,
            message="Fine created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class FineDetailView(APIView):
    """
    GET /api/v1/transactions/fines/{id}/  — retrieve fine detail
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        fine = get_fine_by_id(pk)
        if not fine:
            return error_response(
                message="Fine not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return success_response(data=FineOutputSerializer(fine).data)


class FinePayView(APIView):
    """
    PATCH /api/v1/transactions/fines/{id}/pay/
    Mark a fine as paid. Requires paid_date in the request body.
    """

    permission_classes = [IsStaff]

    def patch(self, request, pk):
        fine = get_fine_by_id(pk)
        if not fine:
            return error_response(
                message="Fine not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Only validate paid-specific fields
        data = {"payment_status": "paid", "paid_date": request.data.get("paid_date")}
        serializer = FinePaymentInputSerializer(data=data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
            )

        try:
            fine = pay_fine(fine=fine, paid_date=serializer.validated_data["paid_date"])
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        fine = get_fine_by_id(fine.pk)
        return success_response(
            data=FineOutputSerializer(fine).data,
            message="Fine marked as paid.",
        )


class FineWaiveView(APIView):
    """
    PATCH /api/v1/transactions/fines/{id}/waive/
    Waive a fine (staff/supervisor discretion).
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        fine = get_fine_by_id(pk)
        if not fine:
            return error_response(
                message="Fine not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            fine = waive_fine(fine=fine)
        except ValueError as exc:
            return error_response(message=str(exc), status_code=status.HTTP_409_CONFLICT)

        fine = get_fine_by_id(fine.pk)
        return success_response(
            data=FineOutputSerializer(fine).data,
            message="Fine waived successfully.",
        )
