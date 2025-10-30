#!/usr/bin/env bash
set -euo pipefail

# Default values
: "${DJANGO_MANAGE_CMD:=python manage.py}"
: "${BIND_ADDR:=0.0.0.0:8000}"

require_var() {
  local name="$1"; shift
  local val="${!name:-}"
  if [ -z "$val" ]; then
    echo "[entrypoint][FATAL] Missing required env: $name" >&2
    exit 1
  fi
}

preflight_prod_checks() {
  # Treat anything other than explicit 'true' as production
  if [ "${DEBUG:-false}" = "true" ] || [ "${DEBUG:-false}" = "True" ]; then
    echo "[entrypoint] DEBUG=true detected. Skipping production preflight checks."
    return 0
  fi

  echo "[entrypoint] Running production preflight checks..."
  require_var DJANGO_SECRET_KEY
  require_var FIELD_ENCRYPTION_KEY
  require_var DB_NAME
  require_var DB_USER
  require_var DB_PASSWORD
  require_var DB_HOST
  require_var ALLOWED_HOSTS
  require_var CSRF_TRUSTED_ORIGINS
  require_var DROPBOX_SIGN_WEBHOOK_SECRET
  require_var DROPBOX_SIGN_API_KEY

  # Service account file should exist and be readable in prod
  SA_FILE="${GOOGLE_SERVICE_ACCOUNT_FILE:-}"
  if [ -z "$SA_FILE" ] || [ ! -r "$SA_FILE" ]; then
    echo "[entrypoint][FATAL] GOOGLE_SERVICE_ACCOUNT_FILE not set or not readable: '$SA_FILE'" >&2
    exit 1
  fi

  echo "[entrypoint] Preflight checks passed."
}

preflight_prod_checks

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

# Optional: seed Sites and Google SocialApp if credentials provided
if { [[ -n "${GOOGLE_CLIENT_ID:-}" && -n "${GOOGLE_CLIENT_SECRET:-}" ]] || [[ -n "${GOOGLE_OAUTH_CLIENT_ID:-}" && -n "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; }; then
  echo "[entrypoint] Seeding Sites and SocialApp..."
  ${DJANGO_MANAGE_CMD} seed_oauth || echo "[entrypoint] seed_oauth failed; continuing"
fi

echo "[entrypoint] Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind "${BIND_ADDR}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}"
