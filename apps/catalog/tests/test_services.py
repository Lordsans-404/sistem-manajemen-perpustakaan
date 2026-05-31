"""
tests/test_services.py — catalog app

Unit tests for:
  - book_service     : create_book, update_book, delete_book
  - book_copy_service: create_book_copy, update_book_copy, delete_book_copy
"""
from unittest.mock import MagicMock, patch

from django.test import TestCase

from django.db.models import ProtectedError

from io import BytesIO

from apps.catalog.models import Book, BookCopy
from apps.catalog.services import (
    create_book,
    create_book_copy,
    delete_book,
    delete_book_copy,
    update_book,
    update_book_copy,
    upload_cover_image,
    delete_cover_image,
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


    def test_delete_book_without_copies_success(self):
        """Book dengan tidak ada copies bisa dihapus."""
        book = make_book()
        pk = book.pk
        delete_book(book=book)
        self.assertFalse(Book.objects.filter(pk=pk).exists())

    def test_delete_book_with_copies_raises_protected_error(self):
        """Book yang masih punya copies tidak bisa dihapus — on_delete=PROTECT."""
        book = make_book()
        library = make_library(code="LIB-PROT")
        BookCopy.objects.create(book=book, library=library)

        with self.assertRaises(ProtectedError):
            delete_book(book=book)


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

# ===========================================================================
# test upload_cover_image
# ===========================================================================

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_upload_returns_public_url(self, mock_get_client):
        """upload_cover_image() return URL yang benar."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        fake_file = BytesIO(b"fake image content")
        fake_file.content_type = "image/jpeg"

        url = upload_cover_image(file=fake_file, filename="cover.jpg")

        # Pastikan upload dipanggil
        mock_client.storage.from_().upload.assert_called_once()

        # Pastikan URL mengandung bucket name dan ekstensi
        self.assertIn("library-storage", url)
        self.assertIn(".jpg", url)

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_upload_generates_unique_filename(self, mock_get_client):
        """Setiap upload punya filename unik — tidak collision."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        fake_file1 = BytesIO(b"image 1")
        fake_file1.content_type = "image/jpeg"
        fake_file2 = BytesIO(b"image 2")
        fake_file2.content_type = "image/jpeg"

        url1 = upload_cover_image(file=fake_file1, filename="cover.jpg")
        url2 = upload_cover_image(file=fake_file2, filename="cover.jpg")

        self.assertNotEqual(url1, url2)  # UUID berbeda tiap upload

# ===========================================================================
# delete_cover_image
# ===========================================================================

class DeleteCoverImageTest(TestCase):

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_delete_calls_supabase_remove(self, mock_get_client):
        """delete_cover_image() memanggil Supabase remove dengan path yang benar."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        url = "https://xxx.supabase.co/storage/v1/object/public/library-storage/covers/abc123.jpg"
        delete_cover_image(url)

        mock_client.storage.from_().remove.assert_called_once_with(["covers/abc123.jpg"])

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_delete_none_url_does_nothing(self, mock_get_client):
        """delete_cover_image(None) tidak crash dan tidak memanggil Supabase."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        delete_cover_image(None)  # tidak boleh raise

        mock_client.storage.from_().remove.assert_not_called()

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_delete_empty_url_does_nothing(self, mock_get_client):
        """delete_cover_image('') tidak crash."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        delete_cover_image("")

        mock_client.storage.from_().remove.assert_not_called()

    @patch("apps.catalog.services.storage_service._get_supabase_client")
    def test_delete_supabase_error_does_not_raise(self, mock_get_client):
        """Kalau Supabase error saat delete, tidak propagate ke caller."""
        mock_client = MagicMock()
        mock_client.storage.from_().remove.side_effect = Exception("Supabase down")
        mock_get_client.return_value = mock_client

        url = "https://xxx.supabase.co/storage/v1/object/public/library-storage/covers/abc.jpg"

        # Tidak boleh raise — storage service sudah handle dengan logger.warning
        try:
            delete_cover_image(url)
        except Exception:
            self.fail("delete_cover_image() raised Exception unexpectedly!")