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
