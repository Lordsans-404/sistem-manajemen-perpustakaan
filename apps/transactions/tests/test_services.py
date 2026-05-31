"""
tests/test_services.py — transactions app

Unit tests for all transaction services:
  - borrow_service  : create_borrow_transaction
  - return_service  : return_book, _create_overdue_fine (idempotency)
  - fine_service    : create_manual_fine, pay_fine, waive_fine
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Book, BookCopy
from apps.transactions.models import BorrowTransaction, Fine
from apps.transactions.services import (
    create_borrow_transaction,
    create_manual_fine,
    pay_fine,
    return_book,
    waive_fine,
)
from apps.users.models import Library, MemberProfile, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="u@test.com"):
    return User.objects.create_user(email=email, name="Test", password="pass1234")


def make_library(code="LIB-TX"):
    return Library.objects.create(name="Lib", code=code, type="central")


def make_book():
    return Book.objects.create(title="Django Deep Dive", author="Author", category="Tech")


def make_book_copy(book, library):
    return BookCopy.objects.create(book=book, library=library)


def make_verified_member(user):
    return MemberProfile.objects.create(
        user=user,
        member_type="student",
        identity_number=f"STD-{uuid.uuid4().hex[:6]}",
        verified_at=timezone.now(),
    )


def make_unverified_member(user):
    return MemberProfile.objects.create(
        user=user,
        member_type="student",
        identity_number=f"UNSTD-{uuid.uuid4().hex[:6]}",
    )


def make_borrow(member, book_copy, library, days_until_due=7):
    today = date.today()
    return BorrowTransaction.objects.create(
        member=member,
        book_copy=book_copy,
        library=library,
        borrow_date=today,
        due_date=today + timedelta(days=days_until_due),
    )


# ===========================================================================
# create_borrow_transaction
# ===========================================================================

class CreateBorrowTransactionServiceTest(TestCase):

    def setUp(self):
        self.library = make_library()
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.user = make_user()
        self.member = make_verified_member(self.user)

    def test_create_borrow_success(self):
        due = date.today() + timedelta(days=7)
        borrow = create_borrow_transaction(
            member=self.member,
            book_copy=self.copy,
            library=self.library,
            due_date=due,
        )
        self.assertIsNotNone(borrow.pk)
        self.assertIsNone(borrow.return_date)
        self.assertEqual(borrow.due_date, due)

    def test_raises_if_member_not_verified(self):
        unverified_user = make_user(email="unver@test.com")
        unverified = make_unverified_member(unverified_user)
        due = date.today() + timedelta(days=7)
        with self.assertRaises(ValueError) as ctx:
            create_borrow_transaction(
                member=unverified,
                book_copy=self.copy,
                library=self.library,
                due_date=due,
            )
        self.assertIn("not verified", str(ctx.exception))

    def test_raises_if_copy_already_on_loan(self):
        due = date.today() + timedelta(days=7)
        create_borrow_transaction(
            member=self.member,
            book_copy=self.copy,
            library=self.library,
            due_date=due,
        )
        # Try borrowing the same copy again
        user2 = make_user(email="u2@test.com")
        member2 = make_verified_member(user2)
        with self.assertRaises(ValueError) as ctx:
            create_borrow_transaction(
                member=member2,
                book_copy=self.copy,
                library=self.library,
                due_date=due,
            )
        self.assertIn("on loan", str(ctx.exception))

    def test_raises_if_due_date_not_in_future(self):
        with self.assertRaises(ValueError) as ctx:
            create_borrow_transaction(
                member=self.member,
                book_copy=self.copy,
                library=self.library,
                due_date=date.today(),  # same day — must be after
            )
        self.assertIn("due_date", str(ctx.exception))

    def test_raises_if_due_date_in_past(self):
        with self.assertRaises(ValueError):
            create_borrow_transaction(
                member=self.member,
                book_copy=self.copy,
                library=self.library,
                due_date=date.today() - timedelta(days=1),
            )


# ===========================================================================
# return_book
# ===========================================================================

class ReturnBookServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-RET")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.user = make_user(email="ret@test.com")
        self.member = make_verified_member(self.user)

    def test_return_on_time_no_fine_created(self):
        """Return before or on due_date → no fine created."""
        borrow = make_borrow(self.member, self.copy, self.library, days_until_due=7)
        return_date = date.today()  # today is before due_date (today + 7 days)
        updated = return_book(borrow=borrow, return_date=return_date)

        self.assertEqual(updated.return_date, return_date)
        self.assertFalse(Fine.objects.filter(borrow_transaction=borrow).exists())

    def test_return_late_creates_overdue_fine(self):
        """Return after due_date → overdue fine auto-created."""
        borrow = make_borrow(self.member, self.copy, self.library, days_until_due=3)
        # Manually backdate the due_date to simulate overdue
        overdue_due = date.today() - timedelta(days=5)
        borrow.due_date = overdue_due
        borrow.save()

        return_date = date.today()
        return_book(borrow=borrow, return_date=return_date)

        fine = Fine.objects.get(borrow_transaction=borrow)
        self.assertEqual(fine.fine_type, Fine.FineType.OVERDUE)
        self.assertEqual(fine.payment_status, Fine.PaymentStatus.UNPAID)
        expected_amount = Decimal("1000.00") * (return_date - overdue_due).days
        self.assertEqual(fine.amount, expected_amount)

    def test_return_calculates_correct_fine_amount(self):
        """Fine = DAILY_FINE_RATE × overdue_days."""
        borrow = make_borrow(self.member, self.copy, self.library, days_until_due=1)
        overdue_due = date.today() - timedelta(days=3)
        borrow.due_date = overdue_due
        borrow.save()

        return_book(borrow=borrow, return_date=date.today())
        fine = Fine.objects.get(borrow_transaction=borrow)
        self.assertEqual(fine.amount, Decimal("3000.00"))  # 3 days × 1000

    def test_raises_if_already_returned(self):
        borrow = make_borrow(self.member, self.copy, self.library)
        borrow.return_date = date.today() - timedelta(days=1)
        borrow.save()

        with self.assertRaises(ValueError) as ctx:
            return_book(borrow=borrow, return_date=date.today())
        self.assertIn("already been returned", str(ctx.exception))

    def test_raises_if_return_date_in_future(self):
        borrow = make_borrow(self.member, self.copy, self.library)
        with self.assertRaises(ValueError) as ctx:
            return_book(borrow=borrow, return_date=date.today() + timedelta(days=1))
        self.assertIn("future", str(ctx.exception))

    def test_return_idempotency_no_duplicate_fine(self):
        """Calling _create_overdue_fine twice should not create duplicate."""
        borrow = make_borrow(self.member, self.copy, self.library, days_until_due=1)
        overdue_due = date.today() - timedelta(days=2)
        borrow.due_date = overdue_due
        borrow.save()

        return_book(borrow=borrow, return_date=date.today())

        # Manually call again (simulate double-trigger)
        from apps.transactions.services.return_service import _create_overdue_fine
        result = _create_overdue_fine(borrow=borrow, return_date=date.today())
        self.assertIsNone(result)
        self.assertEqual(Fine.objects.filter(borrow_transaction=borrow).count(), 1)


# ===========================================================================
# create_manual_fine
# ===========================================================================

class CreateManualFineServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-FINE")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.user = make_user(email="fine@test.com")
        self.member = make_verified_member(self.user)
        self.borrow = make_borrow(self.member, self.copy, self.library)

    def test_create_damage_fine_success(self):
        fine = create_manual_fine(
            borrow=self.borrow,
            fine_type="damage",
            amount=Decimal("50000"),
            description="Book returned with torn pages",
        )
        self.assertEqual(fine.fine_type, "damage")
        self.assertEqual(fine.amount, Decimal("50000"))
        self.assertEqual(fine.payment_status, Fine.PaymentStatus.UNPAID)

    def test_create_loss_fine_success(self):
        fine = create_manual_fine(
            borrow=self.borrow,
            fine_type="loss",
            amount=Decimal("150000"),
            description="Book not returned, declared lost",
        )
        self.assertEqual(fine.fine_type, "loss")

    def test_raises_if_fine_type_is_overdue(self):
        with self.assertRaises(ValueError) as ctx:
            create_manual_fine(
                borrow=self.borrow,
                fine_type="overdue",
                amount=Decimal("1000"),
                description="Overdue",
            )
        self.assertIn("automatically", str(ctx.exception))

    def test_raises_if_fine_already_exists(self):
        create_manual_fine(
            borrow=self.borrow,
            fine_type="damage",
            amount=Decimal("50000"),
            description="First fine",
        )
        with self.assertRaises(ValueError) as ctx:
            create_manual_fine(
                borrow=self.borrow,
                fine_type="loss",
                amount=Decimal("100000"),
                description="Second fine",
            )
        self.assertIn("already exists", str(ctx.exception))

    def test_raises_if_description_empty(self):
        with self.assertRaises(ValueError) as ctx:
            create_manual_fine(
                borrow=self.borrow,
                fine_type="damage",
                amount=Decimal("50000"),
                description="",
            )
        self.assertIn("description", str(ctx.exception))

    def test_raises_if_description_whitespace_only(self):
        with self.assertRaises(ValueError):
            create_manual_fine(
                borrow=self.borrow,
                fine_type="damage",
                amount=Decimal("50000"),
                description="   ",
            )


# ===========================================================================
# pay_fine
# ===========================================================================

class PayFineServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-PAY")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.user = make_user(email="pay@test.com")
        self.member = make_verified_member(self.user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = Fine.objects.create(
            borrow_transaction=self.borrow,
            fine_type="damage",
            amount=Decimal("50000"),
            payment_status=Fine.PaymentStatus.UNPAID,
            description="Test fine",
        )

    def test_pay_fine_success(self):
        today = date.today()
        paid = pay_fine(fine=self.fine, paid_date=today)
        self.assertEqual(paid.payment_status, Fine.PaymentStatus.PAID)
        self.assertEqual(paid.paid_date, today)

    def test_raises_if_already_paid(self):
        pay_fine(fine=self.fine, paid_date=date.today())
        with self.assertRaises(ValueError) as ctx:
            pay_fine(fine=self.fine, paid_date=date.today())
        self.assertIn("already", str(ctx.exception))

    def test_raises_if_fine_waived(self):
        self.fine.payment_status = Fine.PaymentStatus.WAIVED
        self.fine.save()
        with self.assertRaises(ValueError):
            pay_fine(fine=self.fine, paid_date=date.today())

    def test_raises_if_paid_date_in_future(self):
        with self.assertRaises(ValueError) as ctx:
            pay_fine(fine=self.fine, paid_date=date.today() + timedelta(days=1))
        self.assertIn("future", str(ctx.exception))


# ===========================================================================
# waive_fine
# ===========================================================================

class WaiveFineServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-WAIVE")
        self.book = make_book()
        self.copy = make_book_copy(self.book, self.library)
        self.user = make_user(email="waive@test.com")
        self.member = make_verified_member(self.user)
        self.borrow = make_borrow(self.member, self.copy, self.library)
        self.fine = Fine.objects.create(
            borrow_transaction=self.borrow,
            fine_type="damage",
            amount=Decimal("50000"),
            payment_status=Fine.PaymentStatus.UNPAID,
            description="Waive test",
        )

    def test_waive_fine_success(self):
        waived = waive_fine(fine=self.fine)
        self.assertEqual(waived.payment_status, Fine.PaymentStatus.WAIVED)

    def test_raises_if_already_paid(self):
        pay_fine(fine=self.fine, paid_date=date.today())
        with self.assertRaises(ValueError):
            waive_fine(fine=self.fine)

    def test_raises_if_already_waived(self):
        waive_fine(fine=self.fine)
        with self.assertRaises(ValueError):
            waive_fine(fine=self.fine)
