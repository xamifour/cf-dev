#!/usr/bin/env python

# cf-dev/cf_src/manage.py

"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cf.settings")

    # Allow easy placement of apps within the interior appsinn directory.
    current_path = Path(__file__).resolve().parent
    appsinn_path = str(current_path / "appsinn")
    if appsinn_path not in sys.path:
        sys.path.insert(0, appsinn_path)

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
