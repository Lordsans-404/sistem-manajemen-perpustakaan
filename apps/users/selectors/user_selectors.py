from django.contrib.auth import get_user_model

User = get_user_model()


def get_user_by_id(user_id):
    """Return a single User by primary key, or None if not found."""
    return User.objects.filter(pk=user_id).first()


def get_user_by_email(email: str):
    """Return a single User by email (case-insensitive), or None if not found."""
    return User.objects.filter(email__iexact=email).first()


def get_all_users():
    """Return all active users ordered by name."""
    return User.objects.filter(is_active=True).order_by("name")
