from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message: str = None, status_code: int = status.HTTP_200_OK) -> Response:
    """
    Return a standardized success response.

    Shape:
        { "success": true, "message": null, "data": {...} }
    """
    return Response(
        {
            "success": True,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def error_response(message: str, errors=None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """
    Return a standardized error response.

    Shape:
        { "success": false, "message": "...", "errors": {...} }
    """
    return Response(
        {
            "success": False,
            "message": message,
            "errors": errors,
        },
        status=status_code,
    )
