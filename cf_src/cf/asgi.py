# cf-dev/cf_src/cf/asgi.py

"""ASGI config for the CF project."""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

_SRC_ROOT = Path(__file__).resolve().parent.parent
_APPSINN = _SRC_ROOT / "appsinn"
for _path in (str(_APPSINN), str(_SRC_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cf.settings")

application = get_asgi_application()
