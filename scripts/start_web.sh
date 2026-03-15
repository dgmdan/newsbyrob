#!/usr/bin/env bash
set -euo pipefail

PORT=${PORT:-8000}
python manage.py migrate --noinput
exec python manage.py runserver 0.0.0.0:$PORT
