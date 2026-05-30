"""
WSGI config for setup project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.settings')


def _run_migrations_once_on_vercel() -> None:
    if os.getenv("VERCEL") != "1":
        return

    marker = Path("/tmp/.django_migrated")
    if marker.exists():
        return

    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
    marker.touch()


_run_migrations_once_on_vercel()
application = get_wsgi_application()
