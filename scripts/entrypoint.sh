#!/bin/sh
set -e

echo "Applying database migrations..."

echo "Starting supervisor..."
exec supervisord -c /scripts/supervisord.conf