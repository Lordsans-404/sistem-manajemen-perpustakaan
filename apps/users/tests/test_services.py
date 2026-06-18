"""
tests/test_services.py — users app

Unit tests for:
  - user_service  : create_user, update_user, deactivate_user
  - library_service: create_library, update_library, delete_library
  - member_service : create_member_profile, update_member_profile, verify_member
  - staff_service  : create_staff_profile, update_staff_profile

Supabase Auth calls (register_to_supabase, delete_from_supabase) are mocked
via unittest.mock.patch so tests run offline without network access.
"""

import uuid
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.users.models import Library, MemberProfile, StaffProfile, User
from apps.users.services import (
    create_library,
    create_member_profile,
    create_staff_profile,
    create_user,
    deactivate_user,
    delete_library,
    update_library,
    update_member_profile,
    update_staff_profile,
    update_user,
    verify_member,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FAKE_SUPABASE_UID = str(uuid.uuid4())

PATCH_REGISTER = "apps.users.services.user_service.register_to_supabase"
PATCH_DELETE   = "apps.users.services.user_service.delete_from_supabase"


def make_raw_user(email="raw@example.com", name="Raw User"):
    """Create a User directly in DB (bypass Supabase)."""
    return User.objects.create_user(email=email, name=name, password="pass1234")


def make_library(code="LIB-TEST", name="Test Library", type="central"):
    return Library.objects.create(name=name, code=code, type=type)


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class CreateUserServiceTest(TestCase):

    @patch(PATCH_REGISTER, return_value=FAKE_SUPABASE_UID)
    def test_create_user_success(self, mock_register):
        user = create_user(name="Alice", email="alice@example.com", password="pass1234")

        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.name, "Alice")
        self.assertEqual(user.supabase_uid, FAKE_SUPABASE_UID)
        mock_register.assert_called_once_with(email="alice@example.com", password="pass1234")

    @patch(PATCH_REGISTER, return_value=FAKE_SUPABASE_UID)
    def test_create_user_normalizes_email_to_lowercase(self, mock_register):
        user = create_user(name="Bob", email="BOB@EXAMPLE.COM", password="pass1234")
        self.assertEqual(user.email, "bob@example.com")

    @patch(PATCH_REGISTER, return_value=FAKE_SUPABASE_UID)
    def test_create_user_raises_on_duplicate_email(self, mock_register):
        create_user(name="Alice", email="dup@example.com", password="pass1234")
        with self.assertRaises(ValueError) as ctx:
            create_user(name="Alice2", email="dup@example.com", password="pass1234")
        self.assertIn("already exists", str(ctx.exception))

    @patch(PATCH_REGISTER, side_effect=ValueError("Supabase down"))
    def test_create_user_raises_when_supabase_fails(self, mock_register):
        with self.assertRaises(ValueError) as ctx:
            create_user(name="Fail", email="fail@example.com", password="pass1234")
        self.assertIn("Supabase", str(ctx.exception))

    @patch(PATCH_DELETE)
    @patch(PATCH_REGISTER, return_value=FAKE_SUPABASE_UID)
    def test_create_user_rolls_back_supabase_on_db_failure(self, mock_register, mock_delete):
        """If Django DB write fails, Supabase Auth account should be deleted."""
        with patch("apps.users.services.user_service.User.objects.create_user",
                   side_effect=Exception("DB error")):
            with self.assertRaises(Exception):
                create_user(name="Rollback", email="rollback@example.com", password="pass1234")
        mock_delete.assert_called_once_with(uid=FAKE_SUPABASE_UID)

    @patch(PATCH_DELETE, side_effect=RuntimeError("Rollback failed"))
    @patch(PATCH_REGISTER, return_value=FAKE_SUPABASE_UID)
    def test_create_user_logs_critical_when_rollback_fails(self, mock_register, mock_delete):
        """If Django DB write fails AND Supabase rollback fails, original error is still raised."""
        with patch("apps.users.services.user_service.User.objects.create_user",
                   side_effect=Exception("DB error")):
            with patch("apps.users.services.user_service.logger.critical") as mock_critical:
                with self.assertRaises(Exception) as ctx:
                    create_user(name="Orphan", email="orphan@example.com", password="pass1234")
                
                self.assertIn("DB error", str(ctx.exception))
                mock_critical.assert_called_once()
                self.assertIn("DELETE MANUALLY", mock_critical.call_args[0][0])


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

class UpdateUserServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user()

    def test_update_name(self):
        updated = update_user(user=self.user, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_update_phone_number(self):
        updated = update_user(user=self.user, phone_number="081234567890")
        self.assertEqual(updated.phone_number, "081234567890")

    def test_update_strips_whitespace(self):
        updated = update_user(user=self.user, name="  Spaced  ")
        self.assertEqual(updated.name, "Spaced")

    def test_update_no_args_returns_unchanged(self):
        original_name = self.user.name
        updated = update_user(user=self.user)
        self.assertEqual(updated.name, original_name)

    def test_update_phone_to_empty_string_sets_none(self):
        updated = update_user(user=self.user, phone_number="")
        self.assertIsNone(updated.phone_number)


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------

class DeactivateUserServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user()

    def test_deactivate_sets_is_active_false(self):
        self.assertTrue(self.user.is_active)
        deactivate_user(user=self.user)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


# ---------------------------------------------------------------------------
# create_library
# ---------------------------------------------------------------------------

class CreateLibraryServiceTest(TestCase):

    def test_create_library_success(self):
        lib = create_library(name="Perpustakaan Pusat", type="central", code="lib-central")
        self.assertEqual(lib.code, "LIB-CENTRAL")  # normalized UPPER_CASE
        self.assertEqual(lib.name, "Perpustakaan Pusat")

    def test_create_library_normalizes_code_upper(self):
        lib = create_library(name="Teknik", type="faculty", code="lib-ft")
        self.assertEqual(lib.code, "LIB-FT")

    def test_create_library_raises_on_duplicate_code(self):
        create_library(name="A", type="central", code="LIB-DUP")
        with self.assertRaises(ValueError) as ctx:
            create_library(name="B", type="faculty", code="lib-dup")
        self.assertIn("already exists", str(ctx.exception))


# ---------------------------------------------------------------------------
# update_library
# ---------------------------------------------------------------------------

class UpdateLibraryServiceTest(TestCase):

    def setUp(self):
        self.library = make_library(code="LIB-OLD", name="Old Name")

    def test_update_name(self):
        updated = update_library(library=self.library, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_update_code_normalized_upper(self):
        updated = update_library(library=self.library, code="lib-new")
        self.assertEqual(updated.code, "LIB-NEW")

    def test_update_code_conflict_raises(self):
        make_library(code="LIB-CONFLICT")
        with self.assertRaises(ValueError):
            update_library(library=self.library, code="LIB-CONFLICT")

    def test_update_same_code_no_error(self):
        # Updating to same code should not raise
        updated = update_library(library=self.library, code="LIB-OLD")
        self.assertEqual(updated.code, "LIB-OLD")

    def test_update_no_args_returns_unchanged(self):
        updated = update_library(library=self.library)
        self.assertEqual(updated.code, "LIB-OLD")


# ---------------------------------------------------------------------------
# delete_library
# ---------------------------------------------------------------------------

class DeleteLibraryServiceTest(TestCase):

    def test_delete_library_success(self):
        lib = make_library(code="LIB-DEL")
        lib_pk = lib.pk
        delete_library(library=lib)
        self.assertFalse(Library.objects.filter(pk=lib_pk).exists())


# ---------------------------------------------------------------------------
# create_member_profile
# ---------------------------------------------------------------------------

class CreateMemberProfileServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user(email="member@example.com")

    def test_create_member_profile_success(self):
        profile = create_member_profile(
            user=self.user,
            member_type="student",
            identity_number="STD-001",
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.identity_number, "STD-001")
        self.assertEqual(profile.member_level, MemberProfile.MemberLevel.BRONZE)

    def test_create_member_profile_raises_on_duplicate_identity_number(self):
        create_member_profile(user=self.user, member_type="student", identity_number="STD-DUP")
        user2 = make_raw_user(email="other@example.com")
        with self.assertRaises(ValueError) as ctx:
            create_member_profile(user=user2, member_type="student", identity_number="STD-DUP")
        self.assertIn("already in use", str(ctx.exception))

    def test_create_member_profile_raises_if_user_already_has_profile(self):
        create_member_profile(user=self.user, member_type="student", identity_number="STD-001")
        with self.assertRaises(ValueError) as ctx:
            create_member_profile(user=self.user, member_type="student", identity_number="STD-002")
        self.assertIn("already has a member profile", str(ctx.exception))

    def test_create_member_profile_strips_identity_number(self):
        profile = create_member_profile(
            user=self.user,
            member_type="student",
            identity_number="  STD-SPACE  ",
        )
        self.assertEqual(profile.identity_number, "STD-SPACE")


# ---------------------------------------------------------------------------
# update_member_profile
# ---------------------------------------------------------------------------

class UpdateMemberProfileServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user()
        self.profile = MemberProfile.objects.create(
            user=self.user,
            member_type="student",
            identity_number="STD-UPD",
        )

    def test_update_member_type(self):
        updated = update_member_profile(profile=self.profile, member_type="lecturer")
        self.assertEqual(updated.member_type, "lecturer")

    def test_update_member_level(self):
        updated = update_member_profile(profile=self.profile, member_level="gold")
        self.assertEqual(updated.member_level, "gold")

    def test_update_no_args_returns_unchanged(self):
        updated = update_member_profile(profile=self.profile)
        self.assertEqual(updated.member_type, "student")


# ---------------------------------------------------------------------------
# verify_member
# ---------------------------------------------------------------------------

class VerifyMemberServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user()
        self.profile = MemberProfile.objects.create(
            user=self.user,
            member_type="student",
            identity_number="STD-VER",
        )

    def test_verify_member_sets_verified_at(self):
        self.assertFalse(self.profile.is_verified)
        updated = verify_member(profile=self.profile)
        self.assertTrue(updated.is_verified)
        self.assertIsNotNone(updated.verified_at)

    def test_verify_member_is_idempotent(self):
        verify_member(profile=self.profile)
        self.profile.refresh_from_db()
        first_verified_at = self.profile.verified_at

        # Call again — should not change verified_at
        verify_member(profile=self.profile)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verified_at, first_verified_at)


# ---------------------------------------------------------------------------
# create_staff_profile
# ---------------------------------------------------------------------------

class CreateStaffProfileServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user(email="staff@example.com")
        self.library = make_library()

    def test_create_staff_profile_success(self):
        profile = create_staff_profile(
            user=self.user,
            library=self.library,
            role="librarian",
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.library, self.library)
        self.assertEqual(profile.role, "librarian")

    def test_create_staff_profile_sets_user_is_staff_true(self):
        self.assertFalse(self.user.is_staff)
        create_staff_profile(user=self.user, library=self.library, role="librarian")
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_staff)

    def test_create_staff_profile_raises_on_duplicate(self):
        create_staff_profile(user=self.user, library=self.library, role="librarian")
        with self.assertRaises(ValueError) as ctx:
            create_staff_profile(user=self.user, library=self.library, role="admin")
        self.assertIn("already has a staff profile", str(ctx.exception))


# ---------------------------------------------------------------------------
# update_staff_profile
# ---------------------------------------------------------------------------

class UpdateStaffProfileServiceTest(TestCase):

    def setUp(self):
        self.user = make_raw_user(email="staff2@example.com")
        self.library = make_library(code="LIB-A")
        self.library2 = make_library(code="LIB-B", name="Library B")
        self.profile = StaffProfile.objects.create(
            user=self.user, library=self.library, role="librarian"
        )

    def test_update_role(self):
        updated = update_staff_profile(profile=self.profile, role="admin")
        self.assertEqual(updated.role, "admin")

    def test_update_library(self):
        updated = update_staff_profile(profile=self.profile, library=self.library2)
        self.assertEqual(updated.library, self.library2)

    def test_update_no_args_returns_unchanged(self):
        updated = update_staff_profile(profile=self.profile)
        self.assertEqual(updated.role, "librarian")
