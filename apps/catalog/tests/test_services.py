"""
tests/test_services.py — catalog app

Unit tests for:
  - book_service     : create_book, update_book, delete_book
  - book_copy_service: create_book_copy, update_book_copy, delete_book_copy
"""

from django.test import TestCase

from apps.catalog.models import Book, BookCopy
from apps.catalog.services import (
    create_book,
    create_book_copy,
    delete_book,
    delete_book_copy,
    update_book,
    update_book_copy,
)
from apps.users.models import Library


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_library(code="LIB-CAT"):
    return Library.objects.create(name="Catalog Library", code=code, type="central")


def make_book(title="Test Book", author="Test Author", category="Tech"):
    return Book.objects.create(title=title, author=author, category=category)


# ===========================================================================
# create_book
# ===========================================================================

class CreateBookServiceTest(TestCase):

    def test_create_book_success(self):
        book = create_book(title="Django Guide", author="John", category="Tech")
        self.assertEqual(book.title, "Django Guide")
        self.assertEqual(book.author, "John")
        self.assertEqual(book.category, "Tech")
        self.assertIsNotNone(book.pk)

    def test_create_book_strips_whitespace(self):
        book = create_book(title="  Spaced  ", author="  Author  ", category="  Cat  ")
        self.assertEqual(book.title, "Spaced")
        self.assertEqual(book.author, "Author")
        self.assertEqual(book.category, "Cat")

    def test_create_book_persisted_to_db(self):
        book = create_book(title="Persisted", author="Author", category="Cat")
        self.assertTrue(Book.objects.filter(pk=book.pk).exists())


# ===========================================================================
# update_book
# ===========================================================================

class UpdateBookServiceTest(TestCase):

    def setUp(self):
        self.book = make_book()

    def test_update_title(self):
        updated = update_book(book=self.book, title="New Title")
        self.assertEqual(updated.title, "New Title")

    def test_update_author(self):
        updated = update_book(book=self.book, author="New Author")
        self.assertEqual(updated.author, "New Author")

    def test_update_category(self):
        updated = update_book(book=self.book, category="Science")
        self.assertEqual(updated.category, "Science")

    def test_update_strips_whitespace(self):
        updated = update_book(book=self.book, title="  Trimmed  ")
        self.assertEqual(updated.title, "Trimmed")

    def test_update_no_args_returns_unchanged(self):
        original_title = self.book.title
        updated = update_book(book=self.book)
        self.assertEqual(updated.title, original_title)

    def test_update_persisted_to_db(self):
        update_book(book=self.book, title="Updated DB Title")
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "Updated DB Title")


# ===========================================================================
# delete_book
# ===========================================================================

class DeleteBookServiceTest(TestCase):

    def test_delete_book_success(self):
        book = make_book()
        pk = book.pk
        delete_book(book=book)
        self.assertFalse(Book.objects.filter(pk=pk).exists())

    def test_delete_book_cascades_to_copies(self):
        """Deleting a book should remove all its copies (CASCADE)."""
        book = make_book()
        library = make_library()
        copy = BookCopy.objects.create(book=book, library=library)
        copy_pk = copy.pk
        delete_book(book=book)
        self.assertFalse(BookCopy.objects.filter(pk=copy_pk).exists())


# ===========================================================================
# create_book_copy
# ===========================================================================

class CreateBookCopyServiceTest(TestCase):

    def setUp(self):
        self.library = make_library()
        self.book = make_book()

    def test_create_book_copy_success(self):
        copy = create_book_copy(book=self.book, library=self.library)
        self.assertEqual(copy.book, self.book)
        self.assertEqual(copy.library, self.library)
        self.assertEqual(copy.condition, BookCopy.Condition.GOOD)

    def test_create_book_copy_with_optional_fields(self):
        copy = create_book_copy(
            book=self.book,
            library=self.library,
            isbn="978-0-00-000000-0",
            publisher="Penerbit X",
            publication_year=2023,
            condition="new",
        )
        self.assertEqual(copy.isbn, "978-0-00-000000-0")
        self.assertEqual(copy.publisher, "Penerbit X")
        self.assertEqual(copy.publication_year, 2023)
        self.assertEqual(copy.condition, "new")

    def test_create_book_copy_persisted_to_db(self):
        copy = create_book_copy(book=self.book, library=self.library)
        self.assertTrue(BookCopy.objects.filter(pk=copy.pk).exists())


# ===========================================================================
# update_book_copy
# ===========================================================================

class UpdateBookCopyServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-UPD")
        self.book = make_book()
        self.copy = BookCopy.objects.create(book=self.book, library=self.library)

    def test_update_condition(self):
        updated = update_book_copy(copy=self.copy, condition="poor")
        self.assertEqual(updated.condition, "poor")

    def test_update_isbn(self):
        updated = update_book_copy(copy=self.copy, isbn="123-456")
        self.assertEqual(updated.isbn, "123-456")

    def test_update_publisher(self):
        updated = update_book_copy(copy=self.copy, publisher="New Publisher")
        self.assertEqual(updated.publisher, "New Publisher")

    def test_update_publication_year(self):
        updated = update_book_copy(copy=self.copy, publication_year=2024)
        self.assertEqual(updated.publication_year, 2024)

    def test_update_isbn_empty_string_sets_none(self):
        """Passing empty string for isbn should clear it to None."""
        updated = update_book_copy(copy=self.copy, isbn="")
        self.assertIsNone(updated.isbn)

    def test_update_no_args_returns_unchanged(self):
        original_condition = self.copy.condition
        updated = update_book_copy(copy=self.copy)
        self.assertEqual(updated.condition, original_condition)


# ===========================================================================
# delete_book_copy
# ===========================================================================

class DeleteBookCopyServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-DEL")
        self.book = make_book()
        self.copy = BookCopy.objects.create(book=self.book, library=self.library)

    def test_delete_book_copy_success(self):
        pk = self.copy.pk
        delete_book_copy(copy=self.copy)
        self.assertFalse(BookCopy.objects.filter(pk=pk).exists())
