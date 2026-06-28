import uuid

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.users.models import Library, TimestampMixin


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


class Book(TimestampMixin):
    """Bibliographic metadata for a book title."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=255)
    category = models.CharField(max_length=100, db_index=True)
    cover_image = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "books"
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]
        indexes = [
            # --- Book indexes ---
            GinIndex(
                fields=["title"],
                name="book_title_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                fields=["author"],
                name="book_author_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
            GinIndex(
                fields=["category"],
                name="book_category_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.author}"


# ---------------------------------------------------------------------------
# BookCopy
# ---------------------------------------------------------------------------


class BookCopy(TimestampMixin):
    """
    A physical copy of a book stored in a specific library branch.
    Each copy may have its own ISBN, publisher, and condition.
    """

    class Condition(models.TextChoices):
        NEW = "new", "New"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"
        POOR = "poor", "Poor"
        LOST = "lost", "Lost"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="copies",
    )
    library = models.ForeignKey(
        # Cross-app FK — referenced by string to avoid circular import
        Library,
        on_delete=models.PROTECT,
        related_name="book_copies",
    )
    condition = models.CharField(
        max_length=10,
        choices=Condition.choices,
        default=Condition.GOOD,
    )
    isbn = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    publisher = models.CharField(max_length=255, null=True, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "book_copies"
        verbose_name = "Book Copy"
        verbose_name_plural = "Book Copies"
        indexes = [
            # isbn: B-tree for exact lookup + GIN trgm for partial search
            GinIndex(
                fields=["isbn"],
                name="bookcopy_isbn_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
            # publisher: only trgm
            GinIndex(
                fields=["publisher"],
                name="bookcopy_publisher_trgm_idx",
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.book.title} [copy {self.pk}] — {self.library.code}"
