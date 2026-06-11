from apps.catalog.models import BookCopy
from apps.transactions.models import BorrowTransaction

from django.db.models import Exists, OuterRef


def get_book_copy_by_id(copy_id):
    """Return a BookCopy by primary key with related book and library, or None."""
    return (
        BookCopy.objects
        .select_related("book", "library")
        .filter(pk=copy_id)
        .first()
    )


def get_copies_by_book(book_id):
    """Return all copies of a specific book with library info."""
    return (
        BookCopy.objects
        .select_related("book", "library")
        .filter(book_id=book_id)
        .order_by("library__name", "condition")
    )


def get_copies_by_library(library_id):
    """Return all copies stored in a specific library."""
    return (
        BookCopy.objects
        .select_related("book", "library")
        .filter(library_id=library_id)
        .order_by("book__title")
    )


    
def get_available_copies(book_id=None, library_id=None):
    """
    Return copies that are NOT currently borrowed (no active borrow transaction).
    Optionally filter by book or library.
    An 'active' borrow transaction means return_date is NULL.
    """
    active_borrow = BorrowTransaction.objects.filter(
        book_copy=OuterRef("pk"),
        return_date__isnull=True,
    )
    qs = (
        BookCopy.objects
        .select_related("book", "library")
        .annotate(is_borrowed=Exists(active_borrow))
        .filter(is_borrowed=False)
    )
    if book_id:
        qs = qs.filter(book_id=book_id)
    if library_id:
        qs = qs.filter(library_id=library_id)
    return qs.order_by("book__title")


def get_all_book_copies():
    """Return all book copies with book and library relations pre-fetched."""
    return (
        BookCopy.objects
        .select_related("book", "library")
        .order_by("book__title")
    )
