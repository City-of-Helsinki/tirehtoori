#!/bin/bash

set -e

# Wait for the database to be available
if [ -z "$SKIP_DATABASE_CHECK" ] || [ "$SKIP_DATABASE_CHECK" = "0" ]; then
  until nc -z -v -w30 "$DATABASE_HOST" "${DATABASE_PORT:-5432}"
  do
    echo "Waiting for postgres database connection..."
    sleep 1
  done
  echo "Database is up!"
fi

if [[ "$APPLY_MIGRATIONS" = "True" ]]; then
    echo "Applying migrations..."
    ./manage.py migrate --noinput
fi

# Start server
if [[ -n "$*" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "True" ]]; then
    python -Wd ./manage.py runserver 0.0.0.0:8000
else
    uwsgi --ini /app/.docker/uwsgi_configuration.ini
fi
