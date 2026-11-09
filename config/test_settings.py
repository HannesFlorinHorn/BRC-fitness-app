"""Settings for pytest: fixed values so tests run without a .env file."""

import os

# Long enough to pass the weak-key check in settings.py when DEBUG is off.
os.environ.setdefault("SECRET_KEY", "test-only-not-secret-" + "x1y2z3" * 6)
# The test client speaks plain http.
os.environ.setdefault("SECURE_SSL_REDIRECT", "false")

from config.settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
