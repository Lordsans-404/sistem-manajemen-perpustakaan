import logging

from decouple import config
from supabase import create_client

logger = logging.getLogger(__name__)

# Supabase client — uses service role key so it can manage Auth users
# (anon key cannot create/delete auth users server-side)
from functools import lru_cache


@lru_cache(maxsize=1)
def _get_supabase():
    """Lazy Supabase client — created only when first needed, not at import time."""
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_SERVICE_ROLE_KEY"),
    )


def register_to_supabase(*, email: str, password: str) -> str:
    """
    Create a user account in Supabase Auth.
    Returns the Supabase Auth UID on success.
    Raises ValueError if Supabase Auth rejects the registration.
    """
    try:
        response = _get_supabase().auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,   # skip email confirmation for now
        })
        uid = response.user.id
        logger.info("supabase_auth.registered email=%s uid=%s", email, uid)
        return uid
    except Exception as exc:
        logger.error("supabase_auth.register_failed email=%s error=%s", email, exc)
        raise ValueError(f"Supabase Auth registration failed: {exc}")


def delete_from_supabase(*, uid: str) -> None:
    """
    Delete a user from Supabase Auth by UID.
    Used as a rollback if Django DB creation fails after Supabase Auth succeeds.
    """
    try:
        _get_supabase().auth.admin.delete_user(uid)
        logger.info("supabase_auth.deleted uid=%s", uid)
    except Exception as exc:
        logger.error(
            "supabase_auth.delete_failed uid=%s error=%s — manual cleanup required",
            uid, exc,
        )


def login_with_supabase(*, email: str, password: str) -> dict:
    """
    Authenticate user credentials via Supabase Auth.
    Returns a dict with access_token and refresh_token on success.
    Raises ValueError on invalid credentials.
    """
    try:
        response = _get_supabase().auth.sign_in_with_password({
            "email": email,
            "password": password,
        })
        session = response.session
        logger.info("supabase_auth.login_success email=%s", email)
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": "Bearer",
        }
    except Exception as exc:
        logger.warning("supabase_auth.login_failed email=%s error=%s", email, exc)
        raise ValueError("Invalid email or password.")
