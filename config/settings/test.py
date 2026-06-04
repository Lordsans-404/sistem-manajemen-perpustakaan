# config/settings/test.py
#
# Settings KHUSUS untuk `manage.py test`.
#
# Strategi:
#   1. python-decouple membaca .env terlebih dahulu → SECRET_KEY, Supabase vars sudah ada.
#   2. Kita override DATABASES ke SQLite in-memory → tidak perlu koneksi Supabase Postgres.
#   3. Supabase Auth calls di-mock via unittest.mock.patch di setiap test → tidak ada
#      network request ke Supabase Auth service sama sekali.
#   4. JWKS client & Supabase client sudah lazy-init → tidak akan connect saat import.
#   5. Password hashing di-speed up pakai MD5 (unsafe, test-only).
#   6. Logging disederhanakan → tidak buat file log saat test.

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

DEBUG = True
ALLOWED_HOSTS = ["*"]

# ---------------------------------------------------------------------------
# Database — SQLite in-memory
# Alasan: cepat, offline, tidak butuh Supabase Postgres.
# Django test runner auto-create & destroy DB per test run.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ---------------------------------------------------------------------------
# Password hashing — MD5 (test-only, JANGAN pakai di production)
# Alasan: bcrypt/argon2 lambat by design. MD5 buat test jauh lebih cepat.
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Auth password validators — disable di test
# Alasan: test helper make_user() pakai password "pass1234" yang terlalu
#         sederhana untuk validator default. Di test ini tidak relevan.
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = []

# ---------------------------------------------------------------------------
# Email — suppress semua email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# ---------------------------------------------------------------------------
# Logging — minimal, tidak buat file
# Alasan: supaya tidak ada side effect file I/O saat test.
#         Warning+ tetap tampil di console untuk debug.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# ---------------------------------------------------------------------------
# DRF — override authentication untuk test
#
# SupabaseJWTAuthentication adalah default (dari base.py).
# Di integration test, kita pakai force_authenticate() → authentication
# class tidak dieksekusi sama sekali, jadi ini tidak masalah.
#
# Throttling di-nonaktifkan di sini karena test runner memanggil endpoint
# berulang kali dalam hitungan milidetik sehingga AnonRateThrottle (10/min)
# akan mengembalikan 429 dan merusak assertion test.
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # type: ignore[name-defined]  # noqa: F405 — inherited from base.py via *
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
