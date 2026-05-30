import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.users.services.auth_service import delete_from_supabase, register_to_supabase

logger = logging.getLogger(__name__)

User = get_user_model()


def create_user(*, name: str, email: str, password: str, **extra_fields) -> User:
    """
    Create a new User in both Supabase Auth and Django DB.

    Flow:
      1. Register in Supabase Auth → get UID (outside Django transaction).
      2. Create User in Django DB (inside transaction.atomic).
      3. If Django DB fails → rollback Supabase Auth manually via delete_from_supabase.

    Raises ValueError if:
      - Email already taken in Django DB.
      - Supabase Auth registration fails.
    """
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise ValueError(f"A user with email '{email}' already exists.")

    # Step 1 — Register in Supabase Auth first (outside transaction)
    supabase_uid = register_to_supabase(email=email, password=password)

    # Step 2 — Persist to Django DB
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                name=name.strip(),
                password=password,
                supabase_uid=supabase_uid,   # ← bridge for JWT auth
                **extra_fields,
            )
    except Exception as exc:
        # Step 3 — Rollback Supabase Auth if Django DB fails
        logger.error(
            "user.create_failed email=%s — rolling back Supabase Auth uid=%s",
            email, supabase_uid,
        )
        delete_from_supabase(uid=supabase_uid)
        raise

    logger.info("user.created user_id=%s email=%s supabase_uid=%s", user.pk, user.email, supabase_uid)
    return user


def update_user(*, user: User, name: str | None = None, phone_number: str | None = None) -> User:
    """
    Partially update a User's mutable profile fields.
    Only provided (non-None) values are applied.
    """
    updated_fields = []

    if name is not None:
        user.name = name.strip()
        updated_fields.append("name")

    if phone_number is not None:
        user.phone_number = phone_number.strip() or None
        updated_fields.append("phone_number")

    if updated_fields:
        user.save(update_fields=updated_fields + ["updated_at"])
        logger.info("user.updated user_id=%s fields=%s", user.pk, updated_fields)

    return user


def deactivate_user(*, user: User) -> User:
    """Soft-delete a user by setting is_active=False."""
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    logger.info("user.deactivated user_id=%s", user.pk)
    return user
