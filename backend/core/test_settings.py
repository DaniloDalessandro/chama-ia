"""Settings minimos para testes e comandos sem PostgreSQL/Redis/health_check."""
from core.settings import *  # noqa: F401, F403
import os

BASE_DIR_TEST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR_TEST, "test_db.sqlite3"),
    }
}

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in {
    "daphne", "health_check", "health_check.db",
    "health_check.cache", "health_check.storage",
}]

ROOT_URLCONF = "core.test_urls"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
