"""
WSGI config for setup project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sqlite3
from pathlib import Path

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings")


application = get_wsgi_application()
app = application


def _auth_user_table_exists(db_path: Path) -> bool:
    if not db_path.exists():
        return False

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user'"
            )
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def _run_migrations_once_on_vercel() -> None:
    if os.getenv("VERCEL") != "1":
        return

    from django.conf import settings

    db_path = Path(str(settings.DATABASES["default"]["NAME"]))
    marker = Path("/tmp/.django_migrated")

    if marker.exists() and _auth_user_table_exists(db_path):
        return

    try:
        call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
        if not _auth_user_table_exists(db_path):
            raise RuntimeError("migrate ran but auth_user table was not created")
        marker.touch()
    except Exception as exc:
        print(f"[wsgi] migrate on startup failed: {exc}")
        raise


def _ensure_superuser_on_vercel() -> None:
    if os.getenv("VERCEL") != "1":
        return

    username = (os.getenv("VERCEL_SUPERUSER_USERNAME") or "").strip()
    password = os.getenv("VERCEL_SUPERUSER_PASSWORD") or ""
    email = (os.getenv("VERCEL_SUPERUSER_EMAIL") or "").strip()

    if not username or not password:
        print("[wsgi] superuser bootstrap skipped: missing VERCEL_SUPERUSER_USERNAME/PASSWORD")
        return

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )

    changed = False
    if email and user.email != email:
        user.email = email
        changed = True
    if not user.is_staff:
        user.is_staff = True
        changed = True
    if not user.is_superuser:
        user.is_superuser = True
        changed = True
    if not user.is_active:
        user.is_active = True
        changed = True

    user.set_password(password)
    changed = True

    if changed:
        user.save()

    action = "created" if created else "updated"
    print(f"[wsgi] superuser {action}: {username}")


_run_migrations_once_on_vercel()
_ensure_superuser_on_vercel()
