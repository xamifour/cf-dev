# cf-dev/cf_src/cf/celery.py

"""Celery application for the CF project."""

import os
import sys
from pathlib import Path

from celery import Celery

_SRC_ROOT = Path(__file__).resolve().parent.parent
_APPSINN = _SRC_ROOT / "appsinn"
for _path in (str(_APPSINN), str(_SRC_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cf.settings")
os.environ.setdefault("IS_CELERY", "1")

app = Celery("cf")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
