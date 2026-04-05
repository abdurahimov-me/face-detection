#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

echo "Starting supervisor..."
exec supervisord -c /scripts/supervisord.conf