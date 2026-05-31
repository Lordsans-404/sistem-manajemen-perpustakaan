import logging

from apps.catalog.models import Book

logger = logging.getLogger(__name__)


def create_book(*, title: str, author: str, category: str) -> Book:
    """Create and persist a new Book record."""
    book = Book.objects.create(
        title=title.strip(),
        author=author.strip(),
        category=category.strip(),
    )
    logger.info("book.created book_id=%s title=%r", book.pk, book.title)
    return book


def update_book(*, book, title=None, author=None, category=None, cover_image=None):
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
    if cover_image is not None:
        book.cover_image = cover_image
        updated_fields.append("cover_image")

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
