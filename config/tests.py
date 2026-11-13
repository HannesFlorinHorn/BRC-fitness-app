"""Production settings, checked in a separate process because settings are
read once at startup."""

import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCTION = {
    "DJANGO_SETTINGS_MODULE": "config.settings",
    "DEBUG": "false",
    "SECRET_KEY": "a-long-random-production-key-" + "q7w8e9r0t1" * 3,
    "ALLOWED_HOSTS": "training.example.org",
    "CSRF_TRUSTED_ORIGINS": "https://training.example.org",
    # Set explicitly, so a local .env cannot switch them off.
    "SESSION_COOKIE_SECURE": "true",
    "CSRF_COOKIE_SECURE": "true",
    "SECURE_SSL_REDIRECT": "true",
}


def manage(*args, **env):
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=BASE_DIR,
        env={**os.environ, **PRODUCTION, **env},
        capture_output=True,
        text=True,
    )


def test_production_settings_pass_the_deploy_check():
    result = manage("check", "--deploy", "--fail-level", "WARNING")
    assert result.returncode == 0, result.stderr


def test_production_refuses_to_start_with_the_example_key():
    result = manage("check", SECRET_KEY="change-me-local-dev-only")
    assert result.returncode != 0
    assert "SECRET_KEY is too weak" in result.stderr


def test_errors_reach_the_console_but_not_found_does_not():
    script = (
        "import logging;"
        "logging.getLogger('training.methode').error('Methode guide failed');"
        "logging.getLogger('django.request').warning('Not Found: /wp-admin/')"
    )
    result = manage("shell", "-c", script)
    assert "ERROR training.methode: Methode guide failed" in result.stderr
    assert "Not Found" not in result.stderr


def test_database_lives_at_database_path_in_wal_mode(tmp_path):
    path = tmp_path / "db.sqlite3"
    script = (
        "from django.db import connection;"
        "cursor = connection.cursor();"
        "cursor.execute('PRAGMA journal_mode');"
        "print(cursor.fetchone()[0])"
    )
    result = manage("shell", "-c", script, DATABASE_PATH=str(path))
    assert result.stdout.strip().endswith("wal"), result.stderr
    assert path.exists()


def test_collectstatic_fingerprints_the_css_and_its_fonts(tmp_path):
    # STATIC_ROOT points at a temporary folder, so the project's staticfiles/ stays untouched.
    script = (
        "from django.core.management import call_command;"
        "from django.test import override_settings;"
        "from django.contrib.staticfiles.storage import staticfiles_storage as s;"
        f"o = override_settings(STATIC_ROOT={str(tmp_path)!r}); o.enable();"
        "call_command('collectstatic', '--noinput', verbosity=0);"
        "print(s.url('css/custom.css'))"
    )
    result = manage("shell", "-c", script)
    assert result.returncode == 0, result.stderr
    url = result.stdout.strip().splitlines()[-1]
    # A new name for every CSS change, so browsers may cache each one forever.
    assert url.startswith("/static/css/custom.") and url != "/static/css/custom.css"
    css = (tmp_path / url.removeprefix("/static/")).read_text()
    assert "fonts/manrope-latin-400-normal." in css
    assert "manrope-latin-400-normal.woff2" not in css
    assert (tmp_path / (url.removeprefix("/static/") + ".gz")).exists()
