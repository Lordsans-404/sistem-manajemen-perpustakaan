"""
tests/test_views.py — catalog app

Integration tests for all catalog API endpoints.
Uses DRF APIClient + force_authenticate to bypass Supabase JWT.

Endpoints covered:
  GET    /api/v1/catalog/books/
  POST   /api/v1/catalog/books/
  GET    /api/v1/catalog/books/{id}/
  PATCH  /api/v1/catalog/books/{id}/
  DELETE /api/v1/catalog/books/{id}/
  GET    /api/v1/catalog/book-copies/
  POST   /api/v1/catalog/book-copies/
  GET    /api/v1/catalog/book-copies/{id}/
  PATCH  /api/v1/catalog/book-copies/{id}/
  DELETE /api/v1/catalog/book-copies/{id}/
"""

import uuid

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Book, BookCopy
from apps.users.models import Library, StaffProfile, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="u@test.com"):
    return User.objects.create_user(email=email, name="Test", password="pass1234")


def make_library(code="LIB-CAT"):
    return Library.objects.create(name="Catalog Lib", code=code, type="central")


def make_staff(user, library, role="librarian"):
    user.is_staff = True
    user.save()
    return StaffProfile.objects.create(user=user, library=library, role=role)


def make_book():
    return Book.objects.create(title="Test Book", author="Author", category="Tech")


def make_book_copy(book, library, condition="good"):
    return BookCopy.objects.create(book=book, library=library, condition=condition)


# ===========================================================================
# BookListView  GET/POST /api/v1/catalog/books/
# ===========================================================================

class BookListViewTest(APITestCase):
    url = "/api/v1/catalog/books/"

    def setUp(self):
        self.library = make_library()
        self.plain_user = make_user(email="plain@test.com")
        self.staff_user = make_user(email="staff@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_books_authenticated_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data["data"])

    def test_get_books_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_get_books_search_returns_filtered_results(self):
        Book.objects.create(title="Django REST Framework", author="Tom", category="Tech")
        Book.objects.create(title="Python Basics", author="Alice", category="Intro")
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url + "?search=Django")
        self.assertEqual(res.status_code, 200)
        titles = [r["title"] for r in res.data["data"]["results"]]
        self.assertTrue(any("Django" in t for t in titles))

    def test_post_book_as_staff_201(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {
            "title": "New Book",
            "author": "Author A",
            "category": "Fiction",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["title"], "New Book")

    def test_post_book_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.post(self.url, {
            "title": "Denied",
            "author": "X",
            "category": "Y",
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_post_book_missing_required_fields_400(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"title": "Only Title"}, format="json")
        self.assertEqual(res.status_code, 400)


# ===========================================================================
# BookDetailView  GET/PATCH/DELETE /api/v1/catalog/books/{id}/
# ===========================================================================

class BookDetailViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-BD")
        self.book = make_book()
        self.url = f"/api/v1/catalog/books/{self.book.pk}/"
        self.plain_user = make_user(email="plain2@test.com")
        self.staff_user = make_user(email="staff2@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_book_detail_authenticated_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["title"], "Test Book")

    def test_get_book_not_found_404(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(f"/api/v1/catalog/books/{uuid.uuid4()}/")
        self.assertEqual(res.status_code, 404)

    def test_patch_book_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(self.url, {"title": "Updated Title"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["title"], "Updated Title")

    def test_patch_book_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.patch(self.url, {"title": "Hacked"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_delete_book_as_staff_204(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_delete_book_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 403)


# ===========================================================================
# BookCopyListView  GET/POST /api/v1/catalog/book-copies/
# ===========================================================================

class BookCopyListViewTest(APITestCase):
    url = "/api/v1/catalog/book-copies/"

    def setUp(self):
        self.library = make_library(code="LIB-CPL")
        self.book = make_book()
        self.plain_user = make_user(email="plain3@test.com")
        self.staff_user = make_user(email="staff3@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_book_copies_authenticated_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data["data"])

    def test_get_book_copies_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_post_book_copy_as_staff_201(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {
            "book_id": str(self.book.pk),
            "library_id": str(self.library.pk),
            "condition": "new",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["condition"], "new")

    def test_post_book_copy_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.post(self.url, {
            "book_id": str(self.book.pk),
            "library_id": str(self.library.pk),
        }, format="json")
        self.assertEqual(res.status_code, 403)


# ===========================================================================
# BookCopyDetailView  GET/PATCH/DELETE /api/v1/catalog/book-copies/{id}/
# ===========================================================================

class BookCopyDetailViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-CPD")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.url = f"/api/v1/catalog/book-copies/{self.copy.pk}/"
        self.plain_user = make_user(email="plain4@test.com")
        self.staff_user = make_user(email="staff4@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_book_copy_detail_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["condition"], "good")

    def test_get_book_copy_not_found_404(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(f"/api/v1/catalog/book-copies/{uuid.uuid4()}/")
        self.assertEqual(res.status_code, 404)

    def test_patch_book_copy_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(self.url, {"condition": "poor"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["condition"], "poor")

    def test_patch_book_copy_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.patch(self.url, {"condition": "poor"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_delete_book_copy_as_staff_204(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(BookCopy.objects.filter(pk=self.copy.pk).exists())

    def test_delete_book_copy_as_plain_user_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, 403)
