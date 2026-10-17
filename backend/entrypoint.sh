#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating superuser if needed..."
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@chamaia.local')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Admin@ChamIA2024')
if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print('Superuser created: ' + email)
else:
    print('Superuser already exists: ' + email)
"

echo "Starting daphne..."
exec daphne -b 0.0.0.0 -p 8000 core.asgi:application
