import logging

import jwt
from decouple import config
from jwt import PyJWKClient
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS Client — fetches & caches Supabase's public keys automatically
# PyJWKClient handles caching internally; we instantiate once at module level
# so the cache persists across requests within the same process.
# ---------------------------------------------------------------------------

_SUPABASE_PROJECT_REF = config("SUPABASE_PROJECT_REF")
_JWKS_URL = f"https://{_SUPABASE_PROJECT_REF}.supabase.co/auth/v1/.well-known/jwks.json"

_jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True)


class SupabaseJWTAuthentication(BaseAuthentication):
    """
    DRF authentication backend that validates Supabase-issued JWTs.

    Algorithm : ES256 (ECC P-256) — the current Supabase default.
    Bridge    : supabase_uid — extracted from JWT payload["sub"], matched to User.supabase_uid.
                This is immutable even if the user changes their email.
    sso_id    : intentionally left unused here; reserved for future campus SSO.

    On success : returns (user, token_payload).
    On failure : raises AuthenticationFailed — DRF converts this to HTTP 401.
    On absent  : returns None — request treated as anonymous.
    """

    def authenticate(self, request):
        token = self._extract_token(request)
        if token is None:
            return None

        payload = self._decode_token(token)
        user = self._get_user(payload)
        return (user, payload)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_token(self, request) -> str | None:
        """Pull the raw JWT string from the Authorization: Bearer <token> header."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1].strip()
        return token if token else None

    def _decode_token(self, token: str) -> dict:
        """
        Validate the JWT signature using Supabase's public key (JWKS).
        Raises AuthenticationFailed on any validation error.
        """
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                key=signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token has expired. Please log in again.")
        except jwt.InvalidAudienceError:
            raise AuthenticationFailed("Token audience is invalid.")
        except jwt.DecodeError:
            raise AuthenticationFailed("Token is malformed or could not be decoded.")
        except Exception as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise AuthenticationFailed("Token validation failed.")

    def _get_user(self, payload: dict):
        """
        Resolve the Django User from the JWT payload using supabase_uid as the bridge.
        supabase_uid = payload["sub"] — the immutable Supabase Auth UID.
        Raises AuthenticationFailed if the user does not exist or is inactive.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        supabase_uid = payload.get("sub")
        if not supabase_uid:
            raise AuthenticationFailed("Token payload does not contain a subject (sub).")

        try:
            user = User.objects.get(supabase_uid=supabase_uid)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                "No account found for this token. Please register first."
            )

        if not user.is_active:
            raise AuthenticationFailed("This account has been deactivated.")

        return user
