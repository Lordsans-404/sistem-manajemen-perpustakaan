# serializers package — validation & transformation
#
# Exports:
#   book:
#     BookInputSerializer, BookUpdateInputSerializer, BookOutputSerializer
#   book_copy:
#     BookCopyInputSerializer, BookCopyUpdateInputSerializer, BookCopyOutputSerializer

from apps.catalog.serializers.book_serializers import (
    BookInputSerializer,
    BookOutputSerializer,
    BookUpdateInputSerializer,
)
from apps.catalog.serializers.book_copy_serializers import (
    BookCopyInputSerializer,
    BookCopyOutputSerializer,
    BookCopyUpdateInputSerializer,
)

__all__ = [
    # Book
    "BookInputSerializer",
    "BookUpdateInputSerializer",
    "BookOutputSerializer",
    # BookCopy
    "BookCopyInputSerializer",
    "BookCopyUpdateInputSerializer",
    "BookCopyOutputSerializer",
]
