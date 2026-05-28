from django.urls import path

from apps.catalog.views import (
    BookCopyDetailView,
    BookCopyListView,
    BookDetailView,
    BookListView,
)

app_name = "catalog"

urlpatterns = [
    # --- Book ---
    path("books/", BookListView.as_view(), name="book-list"),
    path("books/<uuid:pk>/", BookDetailView.as_view(), name="book-detail"),

    # --- BookCopy ---
    path("book-copies/", BookCopyListView.as_view(), name="book-copy-list"),
    path("book-copies/<uuid:pk>/", BookCopyDetailView.as_view(), name="book-copy-detail"),
]
