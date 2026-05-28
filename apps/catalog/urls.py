from django.urls import path

# Views will be imported and registered here as they are implemented.
# Convention: /api/v1/catalog/...
#
# Planned endpoints:
#   GET    /api/v1/catalog/books/               — list books (with search/filter)
#   POST   /api/v1/catalog/books/               — create book
#   GET    /api/v1/catalog/books/{id}/           — retrieve book
#   PATCH  /api/v1/catalog/books/{id}/           — update book
#   DELETE /api/v1/catalog/books/{id}/           — delete book
#
#   GET    /api/v1/catalog/book-copies/          — list book copies
#   POST   /api/v1/catalog/book-copies/          — add a new physical copy
#   GET    /api/v1/catalog/book-copies/{id}/     — retrieve copy
#   PATCH  /api/v1/catalog/book-copies/{id}/     — update copy condition / info
#   DELETE /api/v1/catalog/book-copies/{id}/     — remove copy

app_name = "catalog"

urlpatterns = [
    # Endpoints will be registered here as views are implemented.
]
