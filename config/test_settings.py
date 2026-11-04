"""Settings for pytest: a fixed secret so tests run without a .env file."""

import os

os.environ.setdefault("SECRET_KEY", "test-only-not-secret")

from config.settings import *  # noqa: E402,F403

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
