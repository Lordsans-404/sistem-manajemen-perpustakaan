import logging

from django.db import transaction

from apps.catalog.models import Book

logger = logging.getLogger(__name__)


def create_book(*, title: str, author: str, category: str) -> Book:
    """Create and persist a new Book record."""
    with transaction.atomic():
        book = Book.objects.create(
            title=title.strip(),
            author=author.strip(),
            category=category.strip(),
        )
    logger.info("book.created book_id=%s title=%r", book.pk, book.title)
    return book


def update_book(
    *,
    book: Book,
    title: str | None = None,
    author: str | None = None,
    category: str | None = None,
) -> Book:
    """Partially update a Book. Only provided (non-None) fields are changed."""
    updated_fields = []

    if title is not None:
        book.title = title.strip()
        updated_fields.append("title")

    if author is not None:
        book.author = author.strip()
        updated_fields.append("author")

    if category is not None:
        book.category = category.strip()
        updated_fields.append("category")

    if updated_fields:
        book.save(update_fields=updated_fields + ["updated_at"])
        logger.info("book.updated book_id=%s fields=%s", book.pk, updated_fields)

    return book


def delete_book(*, book: Book) -> None:
    """
    Delete a Book record.
    Will raise ProtectedError if the book has copies referencing it via CASCADE
    (Django cascades book → copies, so this also removes all BookCopies).
    Inform callers to confirm before deleting.
    """
    book_id = book.pk
    book.delete()
    logger.info("book.deleted book_id=%s", book_id)
