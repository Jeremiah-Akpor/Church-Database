#!/bin/bash

set -e

is_debug() {
  case "${DEBUG:-False}" in
    1|true|TRUE|True|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

echo "Waiting for PostgreSQL..."
until python manage.py shell -c "from django.db import connections; connections['default'].cursor(); print('Database connection successful')" >/dev/null 2>&1; do
  echo "Database not ready yet. Retrying..."
  sleep 1
done
echo "Database is ready"




echo "📦 Collecting static files & running migrations..."
python manage.py check
python manage.py collectstatic --noinput --clear
python manage.py migrate --noinput


echo "Creating superuser if not exists..."
python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if username and email and password:
    if password.lower() in {"admin123", "password", "changeme", "change-me"} or len(password) < 12:
        raise SystemExit(
            "DJANGO_SUPERUSER_PASSWORD is weak. Use at least 12 characters and avoid default values."
        )
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f'Superuser {username} created successfully')
    else:
        print(f'Superuser {username} already exists')
else:
    print('Skipping automatic superuser creation (env vars not fully set).')
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
