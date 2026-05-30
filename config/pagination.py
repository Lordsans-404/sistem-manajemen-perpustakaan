from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for all list endpoints.

    Query params:
      ?page=2          — page number (default: 1)
      ?page_size=20    — items per page (default: 10, max: 100)

    Response shape (wraps our standard { success, message, data } format):
      {
        "success": true,
        "message": null,
        "data": {
          "count": 100,
          "next": "http://.../api/v1/...?page=3",
          "previous": "http://.../api/v1/...?page=1",
          "results": [...]
        }
      }
    """

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "message": None,
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "results": data,
                },
            }
        )
