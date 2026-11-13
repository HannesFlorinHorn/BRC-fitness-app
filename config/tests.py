"""Production settings, checked in a separate process because settings are
read once at startup."""

import http.client
import os
import re
import socket
import subprocess
import sys
import time
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


def test_gunicorn_config_loads_the_app():
    result = subprocess.run(
        [sys.executable, "-m", "gunicorn", "--check-config", "-c", "config/gunicorn.conf.py"],
        cwd=BASE_DIR,
        env={**os.environ, **PRODUCTION},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(port, path, **headers):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path, headers={"Host": "training.example.org", **headers})
    response = conn.getresponse()
    response.body = response.read().decode(errors="replace")
    conn.close()
    return response


def test_gunicorn_serves_pages_and_static_files_behind_caddy(tmp_path):
    # Settings that only move the database and the static files into tmp_path,
    # so this test never touches the project's db.sqlite3 or staticfiles/.
    (tmp_path / "smoke_settings.py").write_text(
        f"from config.settings import *\nSTATIC_ROOT = {str(tmp_path / 'static')!r}\n"
    )
    env = {
        **os.environ,
        **PRODUCTION,
        "DJANGO_SETTINGS_MODULE": "smoke_settings",
        "PYTHONPATH": str(tmp_path),
        "DATABASE_PATH": str(tmp_path / "db.sqlite3"),
    }
    for args in (["migrate"], ["collectstatic", "--noinput"]):
        setup = subprocess.run([sys.executable, "manage.py", *args, "-v0"], cwd=BASE_DIR, env=env, capture_output=True, text=True)
        assert setup.returncode == 0, setup.stderr

    port = free_port()
    # In Docker, Caddy is not 127.0.0.1, so Gunicorn does not trust its headers.
    # Same here (a documentation address), so this proves Django's own setting works.
    server = subprocess.Popen(
        [sys.executable, "-m", "gunicorn", "-c", "config/gunicorn.conf.py", "--bind", f"127.0.0.1:{port}",
         "--workers", "1", "--forwarded-allow-ips", "192.0.2.1"],
        cwd=BASE_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        for _ in range(50):
            try:
                get(port, "/")
                break
            except OSError:
                time.sleep(0.1)
        else:
            server.kill()
            raise AssertionError(server.communicate()[1])

        # Caddy marks requests that came in over HTTPS; anything else is sent there.
        https = {"X-Forwarded-Proto": "https"}
        assert get(port, "/login/").status == 301
        login = get(port, "/login/", **https)
        assert login.status == 200
        assert "Secure" in login.getheader("Set-Cookie")

        # WhiteNoise serves the fingerprinted CSS the page links, cached for good.
        css_url = re.search(r'/static/css/custom\.\w+\.css', login.body).group()
        css = get(port, css_url, **https)
        assert css.status == 200
        assert "immutable" in css.getheader("Cache-Control")
    finally:
        server.terminate()
        server.wait(timeout=10)
