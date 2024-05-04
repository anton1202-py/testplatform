import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyticalplatform.settings")

app = Celery("analyticalplatform")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "periodic-products-parse": {
        "task": "core.tasks.periodic_products_parse",
        "schedule": timedelta(minutes=3),
    }
}
