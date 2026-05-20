# Setup Integrasi Django + Supabase

Dokumentasi ini berdasarkan pengalaman setup langsung, termasuk troubleshooting yang ditemui.

---

## 1. Install Dependencies

```bash
pip install django djangorestframework python-decouple psycopg2-binary supabase gunicorn whitenoise
pip freeze > requirements.txt
```

---

## 2. Konfigurasi .env

```env
# Django
SECRET_KEY=your-secret-key
DJANGO_SETTINGS_MODULE=config.settings.development

# Database — gunakan Pooler, bukan Direct Connection
DB_NAME=postgres
DB_USER=postgres.your-project-id      # ← PENTING: harus menyertakan project ID
DB_PASSWORD=your-db-password
DB_HOST=aws-0-ap-southeast-1.pooler.supabase.com
DB_PORT=6543

# Supabase Client
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Cara ambil nilai-nilai di atas dari Supabase Dashboard

| Variable | Lokasi di Dashboard |
|---|---|
| `DB_*` | Settings → Database → **Connection pooling** |
| `DB_USER` | Format: `postgres.[project-id]` |
| `SUPABASE_URL` | Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Settings → API → `anon public` |
| `SUPABASE_SERVICE_ROLE_KEY` | Settings → API → `service_role secret` |

> **Penting:** `SERVICE_ROLE_KEY` jangan pernah diekspos ke frontend — hanya untuk server-side.

---

## 3. Konfigurasi Database di settings.py

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
            'sslmode': 'require',  # Supabase wajib SSL, tidak perlu setting di dashboard
        },
    }
}
```

---

## 4. Supabase Client

Buat file `supabase_client.py` di root project:

```python
from supabase import create_client, Client
from decouple import config

supabase: Client = create_client(
    config('SUPABASE_URL'),
    config('SUPABASE_ANON_KEY'),  # ganti SERVICE_ROLE_KEY untuk operasi server-side
)
```

---

## 5. Setup Logs (wajib sebelum jalankan apapun)

Kalau konfigurasi logging pakai `FileHandler`, folder `logs/` harus dibuat dulu secara manual — Django tidak otomatis membuatnya.

```bash
mkdir logs
touch logs/.gitkeep
```

Atau biar otomatis, tambahkan ini di `base.py` sebelum blok `LOGGING`:

```python
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)
```

---

## 6. Test Koneksi

```bash
# 1. Cek konfigurasi
python manage.py check --database default

# 2. Test koneksi langsung
python manage.py dbshell

# 3. Jalankan migrasi
python manage.py migrate

# 4. Test Supabase client via Django shell
python manage.py shell
>>> from supabase_client import supabase
>>> print(supabase.table("users").select("*").limit(1).execute())
```

---

## 7. Troubleshooting

### `Network is unreachable` + `IPv4: (none)`
Jaringan kamu tidak support IPv6, sementara direct connection Supabase hanya punya IPv6. Solusi: gunakan **pooler** (port 6543), bukan direct connection (port 5432).

### `FATAL: no tenant identifier provided`
`DB_USER` masih pakai format `postgres` biasa. Untuk pooler harus pakai format `postgres.your-project-id`.

### Cara cek apakah masalah jaringan atau konfigurasi
```bash
curl -v telnet://aws-0-ap-southeast-1.pooler.supabase.com:6543
```
Kalau konek → masalah di konfigurasi. Kalau timeout → masalah jaringan, pakai VPN.

---

## Catatan Penting

**Direct Connection vs Pooler**

| | Direct Connection | Pooler |
|---|---|---|
| Port | 5432 | 6543 |
| DB_USER | `postgres` | `postgres.project-id` |
| IPv4 | ❌ (hanya IPv6) | ✅ |
| Cocok untuk | - | Development & Production |

Selalu gunakan **pooler** untuk menghindari masalah IPv6 dan lebih efisien untuk production.

**SSL**
Supabase sudah enable SSL by default. Tidak perlu setting di dashboard, cukup tambahkan `'sslmode': 'require'` di `OPTIONS` Django.

**Service Role Key**
Gunakan `ANON_KEY` untuk operasi publik, `SERVICE_ROLE_KEY` hanya untuk operasi server-side yang butuh akses penuh (bypass RLS).
