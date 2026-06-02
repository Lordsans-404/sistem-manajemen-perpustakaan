# Gunakan image Python ringan sebagai base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Buat direktori kerja
WORKDIR /app

# Install system dependencies (jika dibutuhkan psycopg2, dll)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code
COPY . /app/

# Kumpulkan static files (agar bisa dilayani oleh WhiteNoise)
# (Membutuhkan dummy SECRET_KEY agar tidak error saat build)
RUN SECRET_KEY=dummy-secret-key-for-build \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    python manage.py collectstatic --noinput

# Jalankan Gunicorn
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 config.wsgi:application
