import uuid

from django.db import models

from apps.users.models import Library, TimestampMixin


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------


class Book(TimestampMixin):
    """Bibliographic metadata for a book title."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500, db_index=True)
    author = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    cover_image = models.URLField(blank=True, null=True)

    class Meta:
        db_table = "books"
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["title"]

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
    isbn = models.CharField(max_length=20, null=True, blank=True)
    publisher = models.CharField(max_length=255, null=True, blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "book_copies"
        verbose_name = "Book Copy"
        verbose_name_plural = "Book Copies"

    def __str__(self):
        return f"{self.book.title} [copy {self.pk}] — {self.library.code}"
