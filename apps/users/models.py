import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


class TimestampMixin(models.Model):
    """Adds created_at / updated_at audit fields to every concrete model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# User Manager
# ---------------------------------------------------------------------------


class UserManager(BaseUserManager):
    """Custom manager for the SSO-based User model."""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra_fields)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(TimestampMixin, AbstractBaseUser, PermissionsMixin):
    """
    Primary user model.
    sso_id maps to the Supabase Auth UID for SSO integration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sso_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="UID from the campus SSO provider (future integration).",
    )
    supabase_uid = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="UID from Supabase Auth. Used as the JWT bridge for authentication.",
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, db_index=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    # Required by AbstractBaseUser
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            # Trigram index: enables fast LIKE '%name%' search (requires pg_trgm extension)
            GinIndex(fields=["name"], name="user_name_trgm_idx", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self):
        return f"{self.name} <{self.email}>"


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


class Library(TimestampMixin):
    """
    A library branch — either central or faculty-level.
    Placed in the users app because StaffProfile is bound to a library;
    catalog and borrow apps reference it via FK.
    """

    class LibraryType(models.TextChoices):
        CENTRAL = "central", "Central"
        FACULTY = "faculty", "Faculty"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(
        max_length=10,
        choices=LibraryType.choices,
        default=LibraryType.CENTRAL,
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique library code (e.g. LIB-CENTRAL, LIB-FT).",
    )

    class Meta:
        db_table = "libraries"
        verbose_name = "Library"
        verbose_name_plural = "Libraries"

    def __str__(self):
        return f"[{self.code}] {self.name}"


# ---------------------------------------------------------------------------
# MemberProfile
# ---------------------------------------------------------------------------


class MemberProfile(TimestampMixin):
    """Library member profile (student, lecturer, staff, public, etc.)."""

    class MemberType(models.TextChoices):
        STUDENT = "student", "Student"
        LECTURER = "lecturer", "Lecturer"
        STAFF = "staff", "Staff"
        PUBLIC = "public", "Public"

    class MemberLevel(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Silver"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    member_type = models.CharField(
        max_length=20,
        choices=MemberType.choices,
        default=MemberType.STUDENT,
    )
    identity_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Student ID / Employee ID / National ID.",
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when membership was verified by staff.",
    )
    member_level = models.CharField(
        max_length=10,
        choices=MemberLevel.choices,
        default=MemberLevel.BRONZE,
    )

    class Meta:
        db_table = "member_profiles"
        verbose_name = "Member Profile"
        verbose_name_plural = "Member Profiles"

    def __str__(self):
        return f"{self.user.name} ({self.identity_number})"

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None


# ---------------------------------------------------------------------------
# StaffProfile
# ---------------------------------------------------------------------------


class StaffProfile(TimestampMixin):
    """Library staff profile, bound to a single library branch."""

    class StaffRole(models.TextChoices):
        LIBRARIAN = "librarian", "Librarian"
        ADMIN = "admin", "Admin"
        SUPERVISOR = "supervisor", "Supervisor"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_profile",
    )
    library = models.ForeignKey(
        Library,
        on_delete=models.PROTECT,
        related_name="staff_members",
    )
    role = models.CharField(
        max_length=20,
        choices=StaffRole.choices,
        default=StaffRole.LIBRARIAN,
    )

    class Meta:
        db_table = "staff_profiles"
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"

    def __str__(self):
        return f"{self.user.name} — {self.get_role_display()} @ {self.library.code}"
