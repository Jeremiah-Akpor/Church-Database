#!/usr/bin/env bash
set -euo pipefail

load_env() {
  if [ -f "$1" ]; then
    set -o allexport
    # shellcheck disable=SC1090
    source "$1"
    set +o allexport
  fi
}

is_debug() {
  case "${DEBUG:-False}" in
    1|true|TRUE|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

load_env ".env"
load_env "/app/.env"


if [ -z "${SECRET_KEY:-}" ]; then
  if is_debug; then
    export SECRET_KEY="dev-only-insecure-secret-key-change-me"
    echo "[WARN] SECRET_KEY not set. Using temporary development key."
  else
    echo "[ERROR] SECRET_KEY must be set in non-debug mode."
    exit 1
  fi
fi

echo "🚀 Starting church backend setup..."

# --- Wait until Postgres accepts connections ---
POSTGRES_HOST="${POSTGRES_HOST:-${DB_HOST:-}}"
POSTGRES_PORT="${POSTGRES_PORT:-${DB_PORT:-5432}}"
POSTGRES_DB="${POSTGRES_DB:-${DB_NAME:-church_db}}"
POSTGRES_USER="${POSTGRES_USER:-${DB_USER:-church_user}}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}"
export POSTGRES_HOST POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD

if [ -n "${POSTGRES_HOST:-}" ]; then
  echo "[INFO] DB settings host=${POSTGRES_HOST} port=${POSTGRES_PORT} db=${POSTGRES_DB} user=${POSTGRES_USER}"
  echo "[WAIT] Waiting for Postgres at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
  until python - <<'PY'
import os

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
dbname = os.environ.get("POSTGRES_DB", "church_db")
user = os.environ.get("POSTGRES_USER", "church_user")
password = os.environ.get("POSTGRES_PASSWORD", "")

connected = False
try:
    import psycopg

    psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    ).close()
    connected = True
except Exception:
    try:
        import psycopg2

        psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
        ).close()
        connected = True
    except Exception:
        connected = False

raise SystemExit(0 if connected else 1)
PY
  do
    sleep 1
  done
  echo "✅ Postgres is ready!"
fi

echo "Running Django checks and migrations..."
python manage.py check
python manage.py migrate --noinput

if is_debug; then
  echo "DEBUG mode: skipping collectstatic."
else
  echo "Production mode: collecting static files."
  python manage.py collectstatic --noinput --clear
fi

echo "Creating superuser if not exists..."
python manage.py shell <<'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if username and email and password:
    if password.lower() in {"admin123", "password", "changeme", "change-me"} or len(password) < 12:
        raise SystemExit(
            "DJANGO_SUPERUSER_PASSWORD is weak. Use at least 12 characters and avoid default values."
        )
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Superuser {username} created successfully")
    else:
        print(f"Superuser {username} already exists")
else:
    print("Skipping automatic superuser creation (env vars not fully set).")
EOF

if [ "$#" -eq 0 ]; then
  if is_debug; then
    echo "Starting Django development server..."
    exec python manage.py runserver 0.0.0.0:8000
  fi

  echo "Starting Django with Gunicorn..."
  exec gunicorn --bind 0.0.0.0:8000 --workers 4 --threads 4 --worker-class gthread --access-logfile - --error-logfile - --capture-output --enable-stdio-inheritance church_project.wsgi:application
fi

exec "$@"
