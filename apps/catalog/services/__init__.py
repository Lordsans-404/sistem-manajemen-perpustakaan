from apps.catalog.services.book_service import (
    create_book,
    delete_book,
    update_book,
)
from apps.catalog.services.book_copy_service import (
    create_book_copy,
    delete_book_copy,
    update_book_copy,
)

__all__ = [
    # book
    "create_book",
    "update_book",
    "delete_book",
    # book copy
    "create_book_copy",
    "update_book_copy",
    "delete_book_copy",
]
