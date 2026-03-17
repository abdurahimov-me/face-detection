#!/bin/bash
set -e

export PYTHONPATH=$(pwd)

cd admin/


python manage.py migrate --noinput

python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='a').exists():
    User.objects.create_superuser('a', 'admin@example.com', 'a')
EOF

exec gunicorn core.wsgi:application --bind 0.0.0.0:8001 --workers 1
