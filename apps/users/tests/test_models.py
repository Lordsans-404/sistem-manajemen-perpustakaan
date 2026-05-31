"""
tests/test_models.py — users app

Tests for model properties and constraints that live in the model layer.
No service calls here — purely testing fields, __str__, and @property.
"""

from django.test import TestCase
from django.utils import timezone

from apps.users.models import Library, MemberProfile, StaffProfile, User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="user@example.com", name="Test User", is_staff=False):
    return User.objects.create_user(
        email=email,
        name=name,
        password="password123",
        is_staff=is_staff,
    )


def make_library(name="Perpustakaan Pusat", code="LIB-CENTRAL", type="central"):
    return Library.objects.create(name=name, code=code, type=type)


# ---------------------------------------------------------------------------
# User Model
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):

    def test_str_representation(self):
        user = make_user(email="alice@example.com", name="Alice")
        self.assertEqual(str(user), "Alice <alice@example.com>")

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_default_is_active_true(self):
        user = make_user()
        self.assertTrue(user.is_active)

    def test_default_is_staff_false(self):
        user = make_user()
        self.assertFalse(user.is_staff)

    def test_supabase_uid_nullable(self):
        user = make_user()
        self.assertIsNone(user.supabase_uid)

    def test_uuid_primary_key(self):
        user = make_user()
        self.assertIsNotNone(user.pk)
        # UUID pk — string length is 32 hex chars + 4 dashes = 36
        self.assertEqual(len(str(user.pk)), 36)


# ---------------------------------------------------------------------------
# Library Model
# ---------------------------------------------------------------------------

class LibraryModelTest(TestCase):

    def test_str_representation(self):
        lib = make_library(code="LIB-FT", name="Perpustakaan Fakultas Teknik")
        self.assertEqual(str(lib), "[LIB-FT] Perpustakaan Fakultas Teknik")

    def test_default_type_central(self):
        lib = Library.objects.create(name="Main", code="MAIN")
        self.assertEqual(lib.type, Library.LibraryType.CENTRAL)

    def test_uuid_primary_key(self):
        lib = make_library()
        self.assertEqual(len(str(lib.pk)), 36)

    def test_code_unique(self):
        make_library(code="LIB-UNIQUE")
        with self.assertRaises(Exception):
            Library.objects.create(name="Another", code="LIB-UNIQUE")


# ---------------------------------------------------------------------------
# MemberProfile Model
# ---------------------------------------------------------------------------

class MemberProfileModelTest(TestCase):

    def setUp(self):
        self.user = make_user(email="member@example.com", name="Budi")
        self.profile = MemberProfile.objects.create(
            user=self.user,
            member_type=MemberProfile.MemberType.STUDENT,
            identity_number="STD-001",
        )

    def test_str_representation(self):
        self.assertEqual(str(self.profile), "Budi (STD-001)")

    def test_is_verified_false_when_not_verified(self):
        self.assertFalse(self.profile.is_verified)

    def test_is_verified_true_when_verified_at_set(self):
        self.profile.verified_at = timezone.now()
        self.profile.save()
        self.assertTrue(self.profile.is_verified)

    def test_default_member_level_bronze(self):
        self.assertEqual(self.profile.member_level, MemberProfile.MemberLevel.BRONZE)

    def test_default_member_type_student(self):
        self.assertEqual(self.profile.member_type, MemberProfile.MemberType.STUDENT)

    def test_identity_number_unique(self):
        user2 = make_user(email="other@example.com")
        with self.assertRaises(Exception):
            MemberProfile.objects.create(
                user=user2,
                member_type=MemberProfile.MemberType.STUDENT,
                identity_number="STD-001",  # duplicate
            )


# ---------------------------------------------------------------------------
# StaffProfile Model
# ---------------------------------------------------------------------------

class StaffProfileModelTest(TestCase):

    def setUp(self):
        self.user = make_user(email="staff@example.com", name="Siti")
        self.library = make_library()
        self.profile = StaffProfile.objects.create(
            user=self.user,
            library=self.library,
            role=StaffProfile.StaffRole.LIBRARIAN,
        )

    def test_str_representation(self):
        expected = "Siti — Librarian @ LIB-CENTRAL"
        self.assertEqual(str(self.profile), expected)

    def test_default_role_librarian(self):
        self.assertEqual(self.profile.role, StaffProfile.StaffRole.LIBRARIAN)

    def test_one_to_one_user_constraint(self):
        with self.assertRaises(Exception):
            StaffProfile.objects.create(
                user=self.user,  # same user — violates OneToOne
                library=self.library,
                role=StaffProfile.StaffRole.ADMIN,
            )
