"""
tests/test_views.py — users app

Integration tests for all users API endpoints.
Uses DRF APIClient + force_authenticate to bypass Supabase JWT.
"""

from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.users.models import Library, MemberProfile, StaffProfile, User

PATCH_REGISTER = "apps.users.services.user_service.register_to_supabase"
PATCH_LOGIN    = "apps.users.views.auth_views.login_with_supabase"


def make_user(email="user@test.com", name="Test User"):
    return User.objects.create_user(email=email, name=name, password="pass1234")


def make_library(code="LIB-TEST", name="Test Library"):
    return Library.objects.create(name=name, code=code, type="central")


def make_member(user, identity_number="STD-001", verified=False):
    profile = MemberProfile.objects.create(
        user=user, member_type="student", identity_number=identity_number,
    )
    if verified:
        profile.verified_at = timezone.now()
        profile.save()
    return profile


def make_staff(user, library, role="librarian"):
    user.is_staff = True
    user.save()
    return StaffProfile.objects.create(user=user, library=library, role=role)


# ===========================================================================
# Auth
# ===========================================================================

class RegisterViewTest(APITestCase):
    url = "/api/v1/users/register/"

    @patch(PATCH_REGISTER, return_value="fake-uid")
    def test_register_success_201(self, _):
        res = self.client.post(self.url, {"name": "Alice", "email": "a@t.com", "password": "pass1234"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["success"])

    @patch(PATCH_REGISTER, return_value="fake-uid")
    def test_register_duplicate_email_400(self, _):
        self.client.post(self.url, {"name": "A", "email": "dup@t.com", "password": "pass1234"}, format="json")
        res = self.client.post(self.url, {"name": "B", "email": "dup@t.com", "password": "pass1234"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_register_missing_fields_400(self):
        res = self.client.post(self.url, {"name": "No Email"}, format="json")
        self.assertEqual(res.status_code, 400)


class LoginViewTest(APITestCase):
    url = "/api/v1/users/login/"

    @patch(PATCH_LOGIN, return_value={"access_token": "tok", "refresh_token": "ref", "token_type": "Bearer"})
    def test_login_success_200(self, _):
        res = self.client.post(self.url, {"email": "u@t.com", "password": "pass1234"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.data["data"])

    @patch(PATCH_LOGIN, side_effect=ValueError("Invalid email or password."))
    def test_login_wrong_creds_401(self, _):
        res = self.client.post(self.url, {"email": "x@t.com", "password": "wrong123"}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_login_missing_password_400(self):
        res = self.client.post(self.url, {"email": "x@t.com"}, format="json")
        self.assertEqual(res.status_code, 400)


# ===========================================================================
# User Me
# ===========================================================================

class UserMeViewTest(APITestCase):
    url = "/api/v1/users/me/"

    def setUp(self):
        self.user = make_user(email="me@test.com", name="Me User")

    def test_get_me_authenticated_200(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["email"], "me@test.com")

    def test_get_me_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_patch_me_updates_name_200(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.patch(self.url, {"name": "Updated"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["name"], "Updated")


# ===========================================================================
# Libraries
# ===========================================================================

class LibraryListViewTest(APITestCase):
    url = "/api/v1/users/libraries/"

    def setUp(self):
        self.library = make_library(code="LIB-MAIN")
        self.plain_user = make_user(email="plain@test.com")
        self.staff_user = make_user(email="staff@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_list_authenticated_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data["data"])

    def test_get_list_unauthenticated_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 401)

    def test_post_as_staff_201(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"name": "New", "type": "faculty", "code": "LIB-NEW"}, format="json")
        self.assertEqual(res.status_code, 201)

    def test_post_as_member_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.post(self.url, {"name": "X", "type": "faculty", "code": "LIB-X"}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_post_duplicate_code_400(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {"name": "Dup", "type": "central", "code": "LIB-MAIN"}, format="json")
        self.assertEqual(res.status_code, 400)


class LibraryDetailViewTest(APITestCase):
    def setUp(self):
        self.library = make_library(code="LIB-DET")
        self.url = f"/api/v1/users/libraries/{self.library.pk}/"
        self.plain_user = make_user(email="plain2@test.com")
        self.staff_user = make_user(email="staff2@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_detail_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["code"], "LIB-DET")

    def test_get_not_found_404(self):
        import uuid
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(f"/api/v1/users/libraries/{uuid.uuid4()}/")
        self.assertEqual(res.status_code, 404)

    def test_patch_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.patch(self.url, {"name": "Renamed"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["name"], "Renamed")

    def test_delete_as_staff_204(self):
        lib = make_library(code="LIB-DEL")
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.delete(f"/api/v1/users/libraries/{lib.pk}/")
        self.assertEqual(res.status_code, 204)


# ===========================================================================
# Members
# ===========================================================================

class MemberListViewTest(APITestCase):
    url = "/api/v1/users/members/"

    def setUp(self):
        self.library = make_library(code="LIB-MEM")
        self.plain_user = make_user(email="plain3@test.com")
        self.staff_user = make_user(email="staff3@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_get_list_200(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_post_as_staff_201(self):
        new_user = make_user(email="newmem@test.com")
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url, {
            "user_id": str(new_user.pk),
            "member_type": "student",
            "identity_number": "STD-POST-001",
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_post_as_plain_403(self):
        new_user = make_user(email="denied_mem@test.com")
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.post(self.url, {
            "user_id": str(new_user.pk),
            "member_type": "student",
            "identity_number": "STD-DEN-001",
        }, format="json")
        self.assertEqual(res.status_code, 403)


class MemberVerifyViewTest(APITestCase):
    def setUp(self):
        self.library = make_library(code="LIB-VER")
        self.member_user = make_user(email="unver@test.com")
        self.member = make_member(self.member_user, identity_number="STD-VER-001")
        self.url = f"/api/v1/users/members/{self.member.pk}/verify/"
        self.staff_user = make_user(email="staffver@test.com")
        make_staff(self.staff_user, self.library, role="librarian")

    def test_verify_as_staff_200(self):
        self.client.force_authenticate(user=self.staff_user)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["data"]["is_verified"])

    def test_verify_as_member_403(self):
        self.client.force_authenticate(user=self.member_user)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 403)

    def test_verify_unauthenticated_401(self):
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 401)


# ===========================================================================
# Staff
# ===========================================================================

class StaffListViewTest(APITestCase):
    url = "/api/v1/users/staff/"

    def setUp(self):
        self.library = make_library(code="LIB-STAFF")
        self.librarian = make_user(email="lib@test.com")
        make_staff(self.librarian, self.library, role="librarian")
        self.admin_user = make_user(email="admin@test.com")
        make_staff(self.admin_user, self.library, role="admin")
        self.plain_user = make_user(email="plain_st@test.com")

    def test_get_as_staff_200(self):
        self.client.force_authenticate(user=self.librarian)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_get_as_plain_403(self):
        self.client.force_authenticate(user=self.plain_user)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 403)

    def test_post_as_admin_201(self):
        new_user = make_user(email="newstaff@test.com")
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post(self.url, {
            "user_id": str(new_user.pk),
            "library_id": str(self.library.pk),
            "role": "librarian",
        }, format="json")
        self.assertEqual(res.status_code, 201)

    def test_post_as_librarian_403(self):
        """Librarian cannot create staff — only admin/supervisor."""
        new_user = make_user(email="newstaff2@test.com")
        self.client.force_authenticate(user=self.librarian)
        res = self.client.post(self.url, {
            "user_id": str(new_user.pk),
            "library_id": str(self.library.pk),
            "role": "librarian",
        }, format="json")
        self.assertEqual(res.status_code, 403)


class StaffDetailViewTest(APITestCase):
    def setUp(self):
        self.library = make_library(code="LIB-STDET")
        self.librarian = make_user(email="libdet@test.com")
        self.staff_profile = make_staff(self.librarian, self.library, role="librarian")
        self.url = f"/api/v1/users/staff/{self.staff_profile.pk}/"
        self.admin_user = make_user(email="admindet@test.com")
        make_staff(self.admin_user, self.library, role="admin")

    def test_get_as_staff_200(self):
        self.client.force_authenticate(user=self.librarian)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def test_patch_as_admin_200(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(self.url, {"role": "admin"}, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["role"], "admin")

    def test_patch_as_librarian_403(self):
        self.client.force_authenticate(user=self.librarian)
        res = self.client.patch(self.url, {"role": "admin"}, format="json")
        self.assertEqual(res.status_code, 403)
