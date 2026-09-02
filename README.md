# Sistem Manajemen Perpustakaan

**Sistem Manajemen Perpustakaan** is a headless, REST API-first library circulation management system built with Django + Django REST Framework. It manages the full lifecycle of book borrowing, returning, and fine settlement — alongside user accounts, library branch organization, and a bibliographic catalog — designed for Indonesian university library settings.

**Frontend**: a separate [React.js app](https://github.com/Lordsans-404/fe-sistem-manajemen-perpustakaan) (deployed on Vercel). This repository is the **backend API only**.

---

## Tech Stack

| Layer             | Technology                                                 |
| -------------------| ------------------------------------------------------------|
| Framework         | Django 5.2, Django REST Framework 3.16                     |
| Language          | Python 3.11+                                               |
| Database          | PostgreSQL via **Supabase** (connection pooler, port 6543) |
| Auth              | Supabase Auth — JWT (ES256), validated server-side         |
| File Storage      | Supabase Storage (book cover images)                       |
| WSGI Server       | Gunicorn                                                   |
| Static Files      | WhiteNoise (CompressedManifestStorage)                     |
| Secrets / Config  | python-decouple                                            |
| Container         | Docker (Python 3.11-slim base)                             |
| Deployment Target | Google Cloud Run                                           |

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** — provided by Supabase (use the **connection pooler**, port `6543`, not direct connection port `5432`)
- **Supabase project** — for database, auth, and storage
- **Docker** (optional, for containerized deployment)
- The `pg_trgm` PostgreSQL extension must be enabled in your Supabase database for full-text / trigram search (GIN indexes). Supabase enables this by default on new projects.

---

## Installation & Setup

### 1. Clone & virtual environment

```bash
git clone <repo-url>
cd sistem-manajemen-perpustakaan
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` at the project root:

```env
# Django
SECRET_KEY=your-random-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.development

# Database — Supabase connection pooler
DB_NAME=postgres
DB_USER=postgres.<your-project-ref>   # must include project ref
DB_PASSWORD=your-db-password
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543

# Supabase Client
SUPABASE_URL=https://<your-project-ref>.supabase.co
SUPABASE_PROJECT_REF=<your-project-ref>
SUPABASE_ANON_KEY=<anon-public-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>   # server-side only, never expose to frontend

# Business rules (with defaults shown)
BORROW_MAX_ACTIVE_BOOKS=5
FINE_PER_DAY_IDR=1000

# Development-only toggles
ALLOW_SELF_MEMBER_REGISTRATION=True
```

> **Pooler note:** Always use the Supabase connection pooler (port `6543`), not direct connection (`5432`), to avoid IPv6 connectivity issues.

### 4. Database setup

```bash
# Verify database connection
python manage.py check --database default

# Run migrations
python manage.py migrate

# Create a superuser (optional — for Django admin at /admin/)
python manage.py createsuperuser
```

### 5. Run the development server

```bash
python manage.py runserver --settings=config.settings.development
# → http://localhost:8000
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django secret key. Use a long random string in production. |
| `DJANGO_SETTINGS_MODULE` | Yes | `config.settings.development` | Which settings file to load (`development`, `production`, or `test`). |
| `DB_NAME` | Yes | `postgres` | PostgreSQL database name. |
| `DB_USER` | Yes | — | Pooler username — must be in format `postgres.<project-ref>`. |
| `DB_PASSWORD` | Yes | — | Pooler password. |
| `DB_HOST` | Yes | — | Pooler hostname, e.g. `aws-0-ap-southeast-1.pooler.supabase.com`. |
| `DB_PORT` | Yes | `6543` | Pooler port. Use `6543` (not `5432`). |
| `SUPABASE_URL` | Yes | — | Supabase project URL, e.g. `https://<ref>.supabase.co`. |
| `SUPABASE_PROJECT_REF` | Yes | — | Supabase project reference ID. |
| `SUPABASE_ANON_KEY` | Yes | — | Supabase anon/public key. Safe to expose to frontend. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | — | Supabase service role key. Server-side only; never expose. |
| `BORROW_MAX_ACTIVE_BOOKS` | No | `5` | Maximum simultaneous active + pending borrows per member. |
| `FINE_PER_DAY_IDR` | No | `1000` | Late-return fine rate per overdue day, in Indonesian Rupiah. |
| `ALLOWED_HOSTS` | Production | — | Comma-separated list of allowed hostnames. |
| `CSRF_TRUSTED_ORIGINS` | Production | — | Comma-separated CSRF-allowed origins (e.g. Vercel frontend URLs). |
| `CORS_ALLOWED_ORIGINS` | Production | — | Comma-separated CORS-allowed origins. |

---

## How to Run

### Development

```bash
python manage.py runserver --settings=config.settings.development
```

- `DEBUG = True`, static files served by Django.
- Email backend prints to console.
- All requests require a valid JWT in `Authorization: Bearer <token>` header (except public catalog read endpoints and auth endpoints).

### Production (bare metal / VM)

Set `DJANGO_SETTINGS_MODULE=config.settings.production` and:

```bash
python manage.py migrate --noinput
gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 --timeout 120 config.wsgi:application
```

- `DEBUG=False`; security headers, SSL redirect, and HSTS are enabled.
- Static files served by WhiteNoise.

### Docker

```bash
docker build -t library-api .
docker run -p 8080:8080 --env-file .env library-api
```

The `Dockerfile`:
- Uses `python:3.11-slim`.
- Installs dependencies from `requirements.txt`.
- Runs `collectstatic` at build time.
- Runs `migrate` on container start, then starts Gunicorn on port `8080`.

### Google Cloud Run

```bash
gcloud run deploy library-api \
  --source . \
  --region asia-southeast1 \
  --set-env-vars DJANGO_SETTINGS_MODULE=config.settings.production
```

Ensure `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `CORS_ALLOWED_ORIGINS` are set as Cloud Run environment variables.

---

## Project Structure

```
sistem-manajemen-perpustakaan/
├── apps/
│   ├── users/          # User accounts, MemberProfile, StaffProfile, Library
│   │   ├── models.py    # User, Library, MemberProfile, StaffProfile
│   │   ├── views.py     # API views
│   │   ├── urls.py      # /users/ routes
│   │   └── tests/       # test_models, test_services, test_views
│   ├── catalog/         # Book, BookCopy, bibliographic metadata
│   │   ├── models.py    # Book, BookCopy
│   │   ├── views.py     # API views
│   │   ├── urls.py      # /catalog/ routes
│   │   └── tests/
│   └── transactions/    # BorrowTransaction, Fine, circulation logic
│       ├── models.py    # BorrowTransaction, Fine
│       ├── views.py     # API views
│       ├── urls.py      # /transactions/ routes
│       └── tests/
├── config/
│   ├── settings/
│   │   ├── base.py        # Shared settings (installed apps, DRF, business rules)
│   │   ├── development.py  # DEBUG=True, console email backend
│   │   ├── production.py   # DEBUG=False, security headers, pooler DB, WhiteNoise
│   │   └── test.py         # SQLite in-memory DB, mocked auth, MD5 passwords
│   ├── urls.py            # Root URL routing → /api/v1/{app}/
│   ├── authentication.py  # Supabase JWT validation (ES256 via JWKS)
│   ├── permissions.py     # IsMember, IsStaff, IsAdmin, IsMemberOrStaff
│   ├── pagination.py      # StandardPagination — wraps DRF paginator in { success, data }
│   └── api_response.py    # success_response() / error_response() helpers
├── docs/
│   ├── specs.md            # Full system specification (Indonesian)
│   └── api/                # Per-app API documentation
│       ├── README.md   # Auth flow, response shapes, seed accounts, permission matrix
│       ├── users.md
│       ├── catalog.md
│       └── transactions.md
├── scripts/
│   └── test_storage.py     # Supabase Storage upload smoke test
├── static/                 # Django static files (collected for production)
├── logs/                   # Django log output (auto-created)
├── supabase_client.py      # Lazy-initialized Supabase Python client (server-side ops)
├── manage.py               # Django management CLI
├── requirements.txt        # Pinned dependency list
└── Dockerfile              # Production Docker image
```

### Key architectural decisions

- **Service layer pattern**: business logic lives in `services/` within each app, not in views or serializers.
- **Selector pattern**: read-only queries are isolated in selector modules.
- **TimestampMixin**: all concrete models inherit `created_at` / `updated_at`.
- **Soft deactivate**: users are deactivated (`is_active=False`), not hard-deleted, to preserve transaction history.
- **No frontend templates**: this is a pure REST API — consumed by a separate [React frontend](https://github.com/Lordsans-404/fe-sistem-manajemen-perpustakaan).

---

## Testing

Tests use Django's built-in test runner with the `test` settings (SQLite in-memory, mocked Supabase auth).

```bash
# Run all tests
python manage.py test --settings=config.settings.test

# Run tests for a specific app
python manage.py test apps.users --settings=config.settings.test
python manage.py test apps.catalog --settings=config.settings.test
python manage.py test apps.transactions --settings=config.settings.test
```

Each app has three test modules:

```
apps/<name>/tests/
├── test_models.py    # Model field/constraint tests
├── test_services.py  # Business logic / service layer tests
└── test_views.py     # API endpoint / integration tests
```

Test coverage target is ≥ 80 % (per `convention.md`).

---

## API Overview

**Base URL**: `http://host/api/v1/`

All endpoints (except catalog reads, register, and login) require:

```
Authorization: Bearer <access_token>
```

Fetch the token via `POST /api/v1/users/login/`.

### Standard response envelopes

**Success:**
```json
{ "success": true, "message": null, "data": { ... } }
```

**Error:**
```json
{ "success": false, "message": "Human-readable error", "errors": null }
```

**Paginated list:**
```json
{
  "success": true, "message": null,
  "data": { "count": 100, "next": "...", "previous": null, "results": [...] }
}
```

### Key endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/users/login/` | Public | Authenticate → get JWT |
| POST | `/users/register/` | Public | Create user account |
| GET | `/users/me/` | Any user | Get current user profile |
| GET/POST | `/users/libraries/` | Any / Staff | List or create library branches |
| GET/POST | `/users/members/` | Any / Staff | List or create member profiles |
| POST | `/users/members/{id}/verify/` | Staff | Verify a member (required before borrowing) |
| GET/POST/PATCH/DELETE | `/catalog/books/` | Public / Staff | Book title CRUD |
| GET/POST/PATCH/DELETE | `/catalog/book-copies/` | Public / Staff | Physical copy CRUD |
| GET/POST | `/transactions/borrows/` | Member/Staff | List/create borrow transactions |
| POST | `/transactions/borrows/{id}/approve/` | Staff | Approve a pending borrow |
| POST | `/transactions/borrows/{id}/reject/` | Staff | Reject a pending borrow |
| POST | `/transactions/borrows/{id}/return/` | Staff | Process a book return (auto-generates overdue fine) |
| GET/POST | `/transactions/fines/` | Any / Staff | List/create fines |
| PATCH | `/transactions/fines/{id}/pay/` | Staff | Mark a fine as paid |
| PATCH | `/transactions/fines/{id}/waive/` | Staff | Waive/forgive a fine |

See `docs/api/` for the full endpoint reference including request/response shapes, business rules, and error codes.

---

## Deployment

1. Set all required environment variables in your hosting platform (Cloud Run env vars, `.env` file, or secrets manager).
2. The `pg_trgm` extension is enabled automatically on new Supabase projects. For existing projects, run `CREATE EXTENSION pg_trgm;` in the Supabase SQL editor.
3. Run `python manage.py migrate` to create all tables.
4. Deploy the Docker image (or push to Cloud Run / your container registry).
5. Point your frontend at the deployed API URL and set `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` accordingly.

---

## Contributing

See [`convention.md`](convention.md) for the full project convention (naming, architecture, testing, git workflow). Key highlights:

- **Architecture**: Feature-First; business logic in `services/` — not in views or serializers.
- **Git branches**: `feature/`, `fix/`, `refactor/` prefix.
- **Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- **No hardcoded values** — use environment variables.
- **Test coverage target**: ≥ 80%, prioritising services → API → models.
