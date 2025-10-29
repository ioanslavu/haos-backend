#!/usr/bin/env bash
set -euo pipefail

# Default values
: "${DJANGO_MANAGE_CMD:=python manage.py}"
: "${BIND_ADDR:=0.0.0.0:8000}"

echo "[entrypoint] Waiting for database ${DB_HOST:-db}:${DB_PORT:-5432}..."
for i in $(seq 1 60); do
  if nc -z "${DB_HOST:-db}" "${DB_PORT:-5432}" >/dev/null 2>&1; then
    echo "[entrypoint] Database is up."
    break
  fi
  echo "[entrypoint] Still waiting... ($i)"; sleep 1
done

echo "[entrypoint] Applying migrations..."
${DJANGO_MANAGE_CMD} migrate --noinput

echo "[entrypoint] Collecting static files..."
${DJANGO_MANAGE_CMD} collectstatic --noinput || echo "[entrypoint] collectstatic skipped or failed; continuing"

echo "[entrypoint] Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind "${BIND_ADDR}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"

