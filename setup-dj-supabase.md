# Django + Supabase Integration Setup

This guide covers the full setup process including troubleshooting. It was written from hands-on experience.

---

## 1. Install Dependencies

```bash
pip install django djangorestframework python-decouple psycopg2-binary supabase gunicorn whitenoise
pip freeze > requirements.txt
```

---

## 2. Configure .env

```env
# Django
SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=config.settings.development

# Database — use the connection pooler, not direct connection
DB_NAME=postgres
DB_USER=postgres.your-project-id      # IMPORTANT: must include project ID
DB_PASSWORD=your-db-password
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543

# Supabase Client
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Where to find these values in the Supabase Dashboard

| Variable | Location in Dashboard |
|---|---|
| `DB_*` | Settings → Database → **Connection pooling** |
| `DB_USER` | Format: `postgres.[project-id]` |
| `SUPABASE_URL` | Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Settings → API → `anon public` |
| `SUPABASE_SERVICE_ROLE_KEY` | Settings → API → `service_role secret` |

> **Important:** Never expose `SERVICE_ROLE_KEY` to the frontend — only use it server-side.

---

## 3. Database Configuration in settings.py

```python
# config/settings/development.py
from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='6543'),
        'OPTIONS': {
            'sslmode': 'require',  # Supabase requires SSL; set in Django, not the dashboard
        },
    }
}
```

---

## 4. Supabase Client

Create `supabase_client.py` in the project root:

```python
from supabase import create_client, Client
from decouple import config

supabase: Client = create_client(
    config('SUPABASE_URL'),
    config('SUPABASE_ANON_KEY'),  # use SERVICE_ROLE_KEY for server-side operations
)
```

---

## 5. Logs Setup (required before running anything)

If logging config uses `FileHandler`, the `logs/` directory must be created manually — Django does not create it automatically.

```bash
mkdir logs
touch logs/.gitkeep
```

Or, to create it automatically, add this to `base.py` before the `LOGGING` block:

```python
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
```

---

## 6. Connection Test

```bash
# 1. Check database configuration
python manage.py check --database default

# 2. Open a database shell
python manage.py dbshell

# 3. Run migrations
python manage.py migrate

# 4. Test Supabase client via Django shell
python manage.py shell
>>> from supabase_client import supabase
>>> print(supabase.table("users").select("*").limit(1).execute())
```

---

## 7. Troubleshooting

### `Network is unreachable` + `IPv4: (none)`

Your network does not support IPv6, but Supabase direct connections only provide IPv6. Solution: use the **connection pooler** (port 6543), not direct connection (port 5432).

### `FATAL: no tenant identifier provided`

`DB_USER` is still using plain `postgres`. For the pooler, the format must be `postgres.your-project-id`.

### How to check if the issue is network or configuration

```bash
curl -v telnet://aws-0-ap-southeast-1.pooler.supabase.com:6543
```

If it connects → the issue is in your configuration. If it times out → the issue is your network; use a VPN.

---

## Important Notes

**Direct Connection vs Pooler**

| | Direct Connection | Pooler |
|---|---|---|
| Port | 5432 | 6543 |
| DB_USER | `postgres` | `postgres.project-id` |
| IPv4 | ❌ (IPv6 only) | ✅ |
| Suitable for | — | Development & Production |

Always use the **pooler** to avoid IPv6 issues and for better production efficiency.

**SSL**

Supabase has SSL enabled by default. No dashboard configuration needed — just add `'sslmode': 'require'` in Django's `OPTIONS`.

**Service Role Key**

Use `ANON_KEY` for public operations and `SERVICE_ROLE_KEY` only for server-side operations that need full access (bypass RLS).