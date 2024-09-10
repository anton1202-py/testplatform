import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyticalplatform.settings")

app = Celery("analyticalplatform",
             include=['unit_economics.periodic_tasks',
                      ])

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "periodic-products-parse": {
        "task": "core.tasks.periodic_products_parse",
        "schedule": timedelta(minutes=3),
    },

    "unit_economics_moy_sklad": {
        "task": "unit_economics.periodic_tasks.update_moy_sklad_product_list",
        "schedule": crontab(hour=1, minute=0)
    },
    "unit_economics_wildberries": {
        "task": "unit_economics.periodic_tasks.update_wildberries_product_list",
        "schedule": crontab(hour=2, minute=0)
    },
    "unit_economics_ozon": {
        "task": "unit_economics.periodic_tasks.update_ozon_product_list",
        "schedule": crontab(hour=2, minute=10)
    },
    "unit_economics_yandex": {
        "task": "unit_economics.periodic_tasks.update_yandex_product_list",
        "schedule": crontab(hour=2, minute=20)
    },
    "unit_economics_product_costprice": {
        "task": "unit_economics.periodic_tasks.moy_sklad_costprice_add_to_db",
        "schedule": crontab(hour=2, minute=30)
    },
    "unit_economics_action_price": {
        "task": "unit_economics.periodic_tasks.action_article_price_to_db",
        "schedule": crontab(hour=3, minute=30)
    },
}
