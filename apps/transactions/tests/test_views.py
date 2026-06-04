"""
tests/test_views.py — transactions app

Integration tests for all transaction API endpoints.
Uses DRF APIClient + force_authenticate to bypass Supabase JWT.

Endpoints covered:
  GET    /api/v1/transactions/borrows/
  POST   /api/v1/transactions/borrows/
  GET    /api/v1/transactions/borrows/{id}/
  POST   /api/v1/transactions/borrows/{id}/return/
  GET    /api/v1/transactions/fines/
  POST   /api/v1/transactions/fines/
  GET    /api/v1/transactions/fines/{id}/
  PATCH  /api/v1/transactions/fines/{id}/pay/
  PATCH  /api/v1/transactions/fines/{id}/waive/
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Book, BookCopy
from apps.transactions.models import BorrowTransaction, Fine
from apps.users.models import Library, MemberProfile, StaffProfile, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="u@test.com"):
    return User.objects.create_user(email=email, name="Test", password="pass1234")


def make_library(code="LIB-TX"):
    return Library.objects.create(name="Library", code=code, type="central")


def make_book():
    return Book.objects.create(title="Test Book", author="Author", category="Tech")


def make_book_copy(book, library):
    return BookCopy.objects.create(book=book, library=library)


def make_verified_member(user, identity_number=None):
    return MemberProfile.objects.create(
        user=user,
        member_type="student",
        identity_number=identity_number or f"STD-{uuid.uuid4().hex[:6]}",
        verified_at=timezone.now(),
    )


def make_unverified_member(user):
    return MemberProfile.objects.create(
        user=user,
        member_type="student",
        identity_number=f"UNSTD-{uuid.uuid4().hex[:6]}",
    )


def make_staff(user, library, role="librarian"):
    user.is_staff = True
    user.save()
    return StaffProfile.objects.create(user=user, library=library, role=role)


def make_borrow(member, book_copy, library, days_until_due=7):
    return BorrowTransaction.objects.create(
        member=member,
        book_copy=book_copy,
        library=library,
        borrow_date=date.today(),
        due_date=date.today() + timedelta(days=days_until_due),
    )


def make_fine(borrow, fine_type="damage", amount="50000"):
    return Fine.objects.create(
        borrow_transaction=borrow,
        fine_type=fine_type,
        amount=Decimal(amount),
        payment_status=Fine.PaymentStatus.UNPAID,
        description="Test fine",
    )


# ===========================================================================
# BorrowListView  GET /api/v1/transactions/borrows/
# ===========================================================================

class BorrowListViewTest(APITestCase):
    url = "/api/v1/transactions/borrows/"

    def setUp(self):
        self.library = make_library(code="LIB-BL")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)

        # Member (verified)
        self.member_user = make_user(email="member@test.com")
        self.member = make_verified_member(self.member_user)

        # Another verified member
        self.other_user = make_user(email="other@test.com")
        self.other_member = make_verified_member(self.other_user)

        # Staff
        self.staff_user = make_user(email="staff@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

        # Unverified member
        self.unver_user = make_user(email="unver@test.com")
        self.unverified_member = make_unverified_member(self.unver_user)

    def test_get_borrows_as_staff_sees_all_200(self):
        """Staff sees all borrow records."""
        make_borrow(self.member, self.copy, self.library)
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data["data"])

    def test_get_borrows_as_member_sees_own_only_200(self):
        """Verified member only sees their own borrows."""
        copy2 = make_book_copy(self.book, self.library)
        make_borrow(self.member, self.copy, self.library)
        make_borrow(self.other_member, copy2, self.library)
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        results = res.data["data"]["results"]
        # BorrowTransactionListOutputSerializer is flat — no nested member object.
        # Verify ownership by checking member_name matches the expected member's user name.
        for item in results:
            self.assertEqual(item["member_name"], self.member.user.name)

    def test_get_borrows_as_member_no_profile_403(self):
        """Authenticated user with no member_profile gets 403."""
        plain_user = make_user(email="noprofile@test.com")
        self.client.force_authenticate(user=plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_get_borrows_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_get_borrows_status_filter_active_as_staff(self):
        make_borrow(self.member, self.copy, self.library)
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(self.url + "?status=active")
        self.assertEqual(res.status_code, 200)
        for item in res.data["data"]["results"]:
            self.assertIsNone(item["return_date"])

    def test_get_borrows_status_filter_active_as_member(self):
        """Member status filter scopes to own borrows only."""
        make_borrow(self.member, self.copy, self.library)
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url + "?status=active")
        self.assertEqual(res.status_code, 200)
        for item in res.data["data"]["results"]:
            self.assertEqual(item["member_name"], self.member.user.name)
            self.assertIsNone(item["return_date"])

    def test_post_borrow_as_verified_member_for_self_201(self):
        self.client.force_authenticate(user=self.member_user)
        res = self.client.post(self.url, {
            "member_id": str(self.member.pk),
            "book_copy_id": str(self.copy.pk),
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertIsNone(res.data["data"]["return_date"])

    def test_post_borrow_as_member_for_other_member_403(self):
        """Member cannot borrow on behalf of a different member."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.post(self.url, {
            "member_id": str(self.other_member.pk),   # <-- different member!
            "book_copy_id": str(self.copy.pk),
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_post_borrow_unverified_member_403(self):
        """Unverified member cannot borrow — is_verified check inside post()."""
        self.client.force_authenticate(user=self.unver_user)
        res = self.client.post(self.url, {
            "member_id": str(self.unverified_member.pk),
            "book_copy_id": str(self.copy.pk),
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 403)

    def test_post_borrow_as_staff_for_any_member_201(self):
        """Staff can create a borrow for any member."""
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {
            "member_id": str(self.member.pk),
            "book_copy_id": str(self.copy.pk),
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_post_borrow_copy_already_on_loan_409(self):
        """Cannot borrow a copy that is already on loan."""
        make_borrow(self.member, self.copy, self.library)
        copy2 = make_book_copy(self.book, self.library)

        user2 = make_user(email="m2@test.com")
        member2 = make_verified_member(user2)
        self.client.force_authenticate(user=user2)
        res = self.client.post(self.url, {
            "member_id": str(member2.pk),
            "book_copy_id": str(self.copy.pk),  # same copy still on loan
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 409)

    def test_post_borrow_as_unauthenticated_401(self):
        res = self.client.post(self.url, {
            "member_id": str(self.member.pk),
            "book_copy_id": str(self.copy.pk),
            "library_id": str(self.library.pk),
            "due_date": str(date.today() + timedelta(days=7)),
        }, format="json")
        self.assertEqual(res.status_code, 401)


# ===========================================================================
# BorrowDetailView  GET /api/v1/transactions/borrows/{id}/
# ===========================================================================

class BorrowDetailViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-BD")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)

        self.member_user = make_user(email="membd@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.url = f"/api/v1/transactions/borrows/{self.borrow.pk}/"

        # Other member (different user)
        self.other_user = make_user(email="otherbd@test.com")
        self.other_member = make_verified_member(self.other_user)

        # Staff
        self.staff_user = make_user(email="staffbd@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_own_borrow_as_member_200(self):
        """Member can view their own borrow detail."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_get_other_borrow_as_member_403(self):
        """Member cannot view another member's borrow."""
        self.client.force_authenticate(user=self.other_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_get_any_borrow_as_staff_200(self):
        """Staff can view any borrow detail."""
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_get_borrow_detail_not_found_404(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(f"/api/v1/transactions/borrows/{uuid.uuid4()}/")
        self.assertEqual(res.status_code, 404)

    def test_get_borrow_detail_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)


# ===========================================================================
# BorrowReturnView  POST /api/v1/transactions/borrows/{id}/return/
# ===========================================================================

class BorrowReturnViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-RET")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.member_user = make_user(email="memret@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library, days_until_due=7)
        self.url = f"/api/v1/transactions/borrows/{self.borrow.pk}/return/"

        self.staff_user = make_user(email="staffret@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_return_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["return_date"], str(date.today()))

    def test_return_late_message_mentions_fine(self):
        """Late return → response message should mention overdue fine."""
        self.borrow.due_date = date.today() - timedelta(days=3)
        self.borrow.save()
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("fine", res.data["message"].lower())

    def test_return_as_member_403(self):
        """Members cannot process returns — only staff can."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.post(self.url, {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_return_unauthenticated_401(self):
        res = self.client.post(self.url, {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_return_already_returned_409(self):
        self.borrow.return_date = date.today() - timedelta(days=1)
        self.borrow.save()
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 409)

    def test_return_not_found_404(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(f"/api/v1/transactions/borrows/{uuid.uuid4()}/return/",
                               {"return_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 404)


# ===========================================================================
# FineListView  GET/POST /api/v1/transactions/fines/
# ===========================================================================

class FineListViewTest(APITestCase):
    url = "/api/v1/transactions/fines/"

    def setUp(self):
        self.library = make_library(code="LIB-FL")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)

        self.member_user = make_user(email="memfl@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = make_fine(self.borrow)

        # Other member with their own borrow+fine
        self.other_user = make_user(email="otherfl@test.com")
        self.other_member = make_verified_member(self.other_user)
        other_copy = make_book_copy(self.book, self.library)
        other_borrow = make_borrow(self.other_member, other_copy, self.library)
        make_fine(other_borrow, amount="99000")

        self.staff_user = make_user(email="stafffl@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_fines_as_staff_sees_all_200(self):
        """Staff sees all fines."""
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["data"]["count"], 2)

    def test_get_fines_as_member_sees_own_only_200(self):
        """Member sees only their own fines."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        results = res.data["data"]["results"]
        # FineOutputSerializer nests BorrowTransactionListOutputSerializer (flat).
        # Verify all results belong to this member via member_name.
        for item in results:
            self.assertEqual(
                item["borrow_transaction"]["member_name"],
                self.member.user.name,
            )

    def test_get_fines_as_user_without_member_profile_403(self):
        """Authenticated user with no member_profile gets 403."""
        plain_user = make_user(email="noprofilefl@test.com")
        self.client.force_authenticate(user=plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_get_fines_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_get_fines_payment_status_filter_as_member(self):
        """payment_status filter is scoped to member's own fines."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url + "?payment_status=unpaid")
        self.assertEqual(res.status_code, 200)
        for item in res.data["data"]["results"]:
            self.assertEqual(item["payment_status"], "unpaid")
            self.assertEqual(
                item["borrow_transaction"]["member_name"],
                self.member.user.name,
            )

    def test_post_manual_fine_as_staff_201(self):
        self.client.force_authenticate(user=self.staff_user)
        # Need a borrow without a fine for this test
        new_copy = make_book_copy(self.book, self.library)
        new_borrow = make_borrow(self.member, new_copy, self.library)
        res = self.client.post(self.url, {
            "borrow_transaction_id": str(new_borrow.pk),
            "fine_type": "damage",
            "amount": "75000.00",
            "description": "Cover is torn",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["fine_type"], "damage")

    def test_post_fine_type_overdue_rejected_409(self):
        """Staff cannot manually create an overdue fine."""
        new_copy = make_book_copy(self.book, self.library)
        new_borrow = make_borrow(self.member, new_copy, self.library)
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {
            "borrow_transaction_id": str(new_borrow.pk),
            "fine_type": "overdue",
            "amount": "1000.00",
            "description": "Should be rejected",
        }, format="json")
        self.assertEqual(res.status_code, 409)

    def test_post_fine_as_member_403(self):
        self.client.force_authenticate(user=self.member_user)
        res = self.client.post(self.url, {
            "borrow_transaction_id": str(self.borrow.pk),
            "fine_type": "damage",
            "amount": "50000.00",
            "description": "Test",
        }, format="json")
        self.assertEqual(res.status_code, 403)


# ===========================================================================
# FineDetailView  GET /api/v1/transactions/fines/{id}/
# ===========================================================================

class FineDetailViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-FD")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)

        self.member_user = make_user(email="memfd@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = make_fine(self.borrow)
        self.url = f"/api/v1/transactions/fines/{self.fine.pk}/"

        # Other member
        self.other_user = make_user(email="otherfd@test.com")
        self.other_member = make_verified_member(self.other_user)

        # Staff
        self.staff_user = make_user(email="stafffd@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_own_fine_as_member_200(self):
        """Member can view their own fine detail."""
        self.client.force_authenticate(user=self.member_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_get_other_fine_as_member_403(self):
        """Member cannot view another member's fine."""
        self.client.force_authenticate(user=self.other_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_get_any_fine_as_staff_200(self):
        """Staff can view any fine detail."""
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_get_fine_not_found_404(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.get(f"/api/v1/transactions/fines/{uuid.uuid4()}/")
        self.assertEqual(res.status_code, 404)


# ===========================================================================
# FinePayView  PATCH /api/v1/transactions/fines/{id}/pay/
# ===========================================================================

class FinePayViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-PAY")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.member_user = make_user(email="mempay@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = make_fine(self.borrow)
        self.url = f"/api/v1/transactions/fines/{self.fine.pk}/pay/"

        self.staff_user = make_user(email="staffpay@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_pay_fine_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(self.url, {"paid_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["payment_status"], "paid")

    def test_pay_fine_as_member_403(self):
        self.client.force_authenticate(user=self.member_user)
        res = self.client.patch(self.url, {"paid_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_pay_already_paid_409(self):
        self.fine.payment_status = Fine.PaymentStatus.PAID
        self.fine.paid_date = date.today()
        self.fine.save()
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(self.url, {"paid_date": str(date.today())}, format="json")
        self.assertEqual(res.status_code, 409)


# ===========================================================================
# FineWaiveView  PATCH /api/v1/transactions/fines/{id}/waive/
# ===========================================================================

class FineWaiveViewTest(APITestCase):

    def setUp(self):
        self.library = make_library(code="LIB-WAI")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.member_user = make_user(email="memwai@test.com")
        self.member = make_verified_member(self.member_user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = make_fine(self.borrow)
        self.url = f"/api/v1/transactions/fines/{self.fine.pk}/waive/"

        # Librarian (IsStaff but NOT IsAdmin)
        self.librarian_user = make_user(email="libwai@test.com")
        make_staff(self.librarian_user, self.library, role="librarian")

        # Admin (IsAdmin)
        self.admin_user = make_user(email="adminwai@test.com")
        make_staff(self.admin_user, self.library, role="admin")

    def test_waive_fine_as_admin_200(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["payment_status"], "waived")

    def test_waive_fine_as_librarian_403(self):
        """Librarian cannot waive fines — only admin/supervisor."""
        self.client.force_authenticate(user=self.librarian_user)
        res = self.client.patch(self.url)
        self.assertEqual(res.status_code, 403)

    def test_waive_fine_as_member_403(self):
        self.client.force_authenticate(user=self.member_user)
        res = self.client.patch(self.url)
        self.assertEqual(res.status_code, 403)

    def test_waive_already_paid_409(self):
        self.fine.payment_status = Fine.PaymentStatus.PAID
        self.fine.paid_date = date.today()
        self.fine.save()
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(self.url)
        self.assertEqual(res.status_code, 409)

    def test_waive_unauthenticated_401(self):
        res = self.client.patch(self.url)
        self.assertEqual(res.status_code, 401)
