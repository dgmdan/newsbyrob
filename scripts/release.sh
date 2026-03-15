#!/usr/bin/env bash
set -euo pipefail

python scripts/ensure_schema.py
python manage.py migrate --noinput
