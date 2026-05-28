import logging

from django.contrib.auth import get_user_model
from django.db import transaction

logger = logging.getLogger(__name__)

User = get_user_model()


def create_user(*, name: str, email: str, password: str, **extra_fields) -> User:
    """
    Create and persist a new User.
    Raises ValueError if the email is already taken.
    """
    email = email.strip().lower()
    if User.objects.filter(email=email).exists():
        raise ValueError(f"A user with email '{email}' already exists.")

    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            name=name.strip(),
            password=password,
            **extra_fields,
        )

    logger.info("user.created user_id=%s email=%s", user.pk, user.email)
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
