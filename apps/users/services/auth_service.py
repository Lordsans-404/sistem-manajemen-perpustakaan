import logging
from functools import lru_cache

from decouple import config
from supabase import create_client

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_admin_client():
    """
    Cached Supabase client with service role key.
    Used ONLY for admin operations (create_user, delete_user).

    IMPORTANT: sign_in_with_password() must NEVER be called on this client.
    Doing so would overwrite the internal session with a user token, causing
    subsequent admin.create_user() calls to fail with 403 'User not allowed'.
    """
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_SERVICE_ROLE_KEY"),
    )


def _new_anon_client():
    """
    Fresh Supabase client per-request with anon key.
    Used for user-level auth (sign_in_with_password) so that user sessions
    are never stored in a shared/cached client.
    """
    return create_client(
        config("SUPABASE_URL"),
        config("SUPABASE_ANON_KEY"),
    )


def register_to_supabase(*, email: str, password: str) -> str:
    """
    Create a user account in Supabase Auth.
    Returns the Supabase Auth UID on success.
    Raises ValueError if Supabase Auth rejects the registration.
    """
    try:
        response = _get_admin_client().auth.admin.create_user({
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

    Raises RuntimeError if the delete fails — caller must handle this so the
    orphaned Supabase Auth entry does not silently block future registrations.
    """
    try:
        _get_admin_client().auth.admin.delete_user(uid)
        logger.info("supabase_auth.deleted uid=%s", uid)
    except Exception as exc:
        logger.error(
            "supabase_auth.delete_failed uid=%s error=%s — MANUAL CLEANUP REQUIRED in Supabase dashboard",
            uid, exc,
        )
        raise RuntimeError(
            f"Supabase Auth rollback failed for uid={uid}. "
            "The entry must be deleted manually from the Supabase dashboard."
        ) from exc


def login_with_supabase(*, email: str, password: str) -> dict:
    """
    Authenticate user credentials via Supabase Auth.
    Returns a dict with access_token and refresh_token on success.
    Raises ValueError on invalid credentials.
    """
    try:
        response = _new_anon_client().auth.sign_in_with_password({
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
