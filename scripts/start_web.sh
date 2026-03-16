#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}
python manage.py migrate --noinput
WEB_CONCURRENCY=${WEB_CONCURRENCY:-3}
exec gunicorn newsbyrob_site.wsgi:application \
    --bind 0.0.0.0:"$PORT" \
    --workers "$WEB_CONCURRENCY" \
    --access-logfile - \
    --error-logfile -
