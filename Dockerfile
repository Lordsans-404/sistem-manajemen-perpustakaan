# Gunakan image Python ringan sebagai base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install system dependencies (dengan root)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Ganti ownership folder kerja ke user 1000
RUN chown -R user:user $HOME/app

# Pindah ke user 1000
USER user

# Install python dependencies
COPY --chown=user requirements.txt $HOME/app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code
COPY --chown=user . $HOME/app/

# Kumpulkan static files (agar bisa dilayani oleh WhiteNoise)
RUN SECRET_KEY=dummy \
    SUPABASE_URL=dummy \
    SUPABASE_PROJECT_REF=dummy \
    SUPABASE_ANON_KEY=dummy \
    SUPABASE_SERVICE_ROLE_KEY=dummy \
    DB_NAME=dummy \
    DB_USER=dummy \
    DB_PASSWORD=dummy \
    DB_HOST=dummy \
    ALLOWED_HOSTS=dummy \
    CSRF_TRUSTED_ORIGINS=dummy \
    CORS_ALLOWED_ORIGINS=dummy \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    python manage.py collectstatic --noinput

# Jalankan Gunicorn
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 config.wsgi:application
