#!/bin/sh
set -e


echo "Applying database migrations..."
alembic upgrade head

# Start FastAPI (this should be the last command)
exec gunicorn -c gunicorn_conf.py main:app
