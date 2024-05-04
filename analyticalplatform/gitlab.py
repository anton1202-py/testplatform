# -*- coding: utf-8 -*-
# flake8: noqa
from analyticalplatform.settings import *

BROKER_URL = "redis://redis:6379/0"

DATABASES["default"]["HOST"] = "postgres"
DATABASES["default"]["NAME"] = os.environ.get("POSTGRES_DB")
DATABASES["default"]["USER"] = os.environ.get("POSTGRES_USER")
DATABASES["default"]["PASSWORD"] = os.environ.get("POSTGRES_PASSWORD")
DATABASES["default"]["PORT"] = "5432"

CACHEOPS_REDIS = {"host": "redis", "port": 6379, "db": 1}
