import logging

from django.db import transaction

from apps.catalog.models import Book, BookCopy
from apps.users.models import Library

logger = logging.getLogger(__name__)


def create_book_copy(
    *,
    book: Book,
    library: Library,
    condition: str = BookCopy.Condition.GOOD,
    isbn: str | None = None,
    publisher: str | None = None,
    publication_year: int | None = None,
) -> BookCopy:
    """Create a new physical copy of a book stored at a library branch."""
    with transaction.atomic():
        copy = BookCopy.objects.create(
            book=book,
            library=library,
            condition=condition,
            isbn=isbn,
            publisher=publisher,
            publication_year=publication_year,
        )
    logger.info(
        "book_copy.created copy_id=%s book_id=%s library=%s",
        copy.pk, book.pk, library.code,
    )
    return copy


def update_book_copy(
    *,
    copy: BookCopy,
    condition: str | None = None,
    isbn: str | None = None,
    publisher: str | None = None,
    publication_year: int | None = None,
) -> BookCopy:
    """Partially update a BookCopy's mutable fields."""
    updated_fields = []

    if condition is not None:
        copy.condition = condition
        updated_fields.append("condition")

    if isbn is not None:
        copy.isbn = isbn.strip() or None
        updated_fields.append("isbn")

    if publisher is not None:
        copy.publisher = publisher.strip() or None
        updated_fields.append("publisher")

    if publication_year is not None:
        copy.publication_year = publication_year
        updated_fields.append("publication_year")

    if updated_fields:
        copy.save(update_fields=updated_fields + ["updated_at"])
        logger.info("book_copy.updated copy_id=%s fields=%s", copy.pk, updated_fields)

    return copy


def delete_book_copy(*, copy: BookCopy) -> None:
    """
    Delete a BookCopy.
    Will raise ProtectedError if there is an active borrow transaction for this copy.
    """
    copy_id = copy.pk
    copy.delete()
    logger.info("book_copy.deleted copy_id=%s", copy_id)
