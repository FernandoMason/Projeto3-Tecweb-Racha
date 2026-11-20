#!/usr/bin/env bash
# Build do backend no Render (#17): dependencias, arquivos estaticos do admin e migracoes no PostgreSQL.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
