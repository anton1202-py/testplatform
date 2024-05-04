#!/bin/bash

if [ "$DB_ENGINE" == "django.db.backends.postgresql_psycopg2" ]
then
  until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB" -c '\l'; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
  done
fi

python manage.py migrate
python manage.py collectstatic --no-input --clear
export DJANGO_SETTINGS_MODULE="analyticalplatform.settings"

gunicorn --bind 0.0.0.0:8000 analyticalplatform.wsgi:application --workers=6 --log-level debug
exec "$@"
