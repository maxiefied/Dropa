#!/usr/bin/env bash
# Runs on the live site every time you deploy.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# First deploy only: create your admin account from environment variables
# (DJANGO_SUPERUSER_PHONE, DJANGO_SUPERUSER_NAME, DJANGO_SUPERUSER_PASSWORD).
# Remove DJANGO_SUPERUSER_PASSWORD from the host afterwards.
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi
