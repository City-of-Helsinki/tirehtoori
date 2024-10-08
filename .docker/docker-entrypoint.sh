#!/bin/bash

set -e

if [[ "$APPLY_MIGRATIONS" = "True" ]]; then
    echo "Applying migrations..."
    ./manage.py migrate --noinput
fi

# Create admin user. Generate password if there isn't one in the environment variables
if [[ "$CREATE_SUPERUSER" = "True" ]]; then
    if [[ "$ADMIN_USER_PASSWORD" ]]; then
      ./manage.py add_admin_user -u "${ADMIN_USER_USERNAME:-admin}" -p "$ADMIN_USER_PASSWORD" -e "${ADMIN_USER_EMAIL:-admin@example.com}"
    else
      ./manage.py add_admin_user -u "${ADMIN_USER_USERNAME:-admin}" -e "${ADMIN_USER_EMAIL:-admin@example.com}"
    fi
fi

# Start server
if [[ -n "$*" ]]; then
    "$@"
elif [[ "$DEV_SERVER" = "True" ]]; then
    python -Wd ./manage.py runserver 0.0.0.0:8000
else
    uwsgi --ini /app/.docker/uwsgi_configuration.ini
fi
