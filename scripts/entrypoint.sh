#!/bin/sh
set -e

echo "Starting supervisor..."
exec supervisord -c /scripts/supervisord.conf
