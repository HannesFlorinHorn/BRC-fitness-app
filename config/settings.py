"""
Django settings for the training tracker.

Every value that differs between machines comes from the environment
(see .env.example). Defaults are safe for production; local development
overrides them in .env.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name):
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def is_weak_secret(key):
    """The example key from .env.example, or one Django's deploy check calls weak."""
    return key.startswith("change-me") or len(key) < 50 or len(set(key)) < 5


SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be set in the environment or .env")

DEBUG = env_bool("DEBUG", False)
# Going live with the public example key would let anyone forge signed data,
# so production refuses to start instead of only warning.
if not DEBUG and is_weak_secret(SECRET_KEY):
    raise ImproperlyConfigured(
        "SECRET_KEY is too weak for DEBUG=false. Generate one with the command in .env.example."
    )
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "training",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.session_lifetime.SessionLifetimeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # In Docker the database lives on a volume, outside the replaceable image.
        "NAME": Path(os.environ.get("DATABASE_PATH") or BASE_DIR / "db.sqlite3"),
        # Several Gunicorn workers share one file. WAL lets reads and writes run
        # side by side, a second writer waits up to 5 seconds instead of failing
        # with "database is locked", and IMMEDIATE takes the write lock at the
        # start of a transaction (waiting does not help a lock taken halfway).
        # Write safety (PRAGMA synchronous) stays at SQLite's strict default.
        "OPTIONS": {
            "init_command": "PRAGMA journal_mode=WAL",
            "timeout": 5,
            "transaction_mode": "IMMEDIATE",
        },
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "training:history"
LOGOUT_REDIRECT_URL = "login"

# Logins expire after this much inactivity; every request restarts the timer.
# Athletes stay logged in on their phone across training days; staff accounts
# can read everyone's data, so they time out quickly (accounts/session_lifetime.py).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
STAFF_SESSION_AGE = 60 * 30  # 30 minutes
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SESSION_COOKIE_HTTPONLY = True

# HTTPS. In production Caddy handles HTTPS and passes requests on as plain
# HTTP, noting the original scheme in X-Forwarded-Proto. Trusting that header
# is only safe because Gunicorn is reachable through Caddy alone, never directly.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Caddy redirects to HTTPS too; this is the second safety net. Off locally (.env).
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
# Browsers remember "HTTPS only" for this long. Start low so a broken
# certificate locks nobody out for long; raise to a year once stable (ROADMAP).
SECURE_HSTS_SECONDS = 60 * 60  # 1 hour
# Subdomains and the browsers' preload list stay off on purpose (the domain
# may host other things; preload is hard to undo), so silence those warnings.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# collectstatic copies every static file here, for WhiteNoise to serve in production.
STATIC_ROOT = BASE_DIR / "staticfiles"

# collectstatic stores fingerprinted, compressed copies (custom.3f9a1c2b.css),
# so browsers may cache them forever and still get every CSS change at once.
# With DEBUG off, every page needs them: run collectstatic before starting.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Warnings and errors go to the console (docker compose logs in production,
# the runserver terminal locally). Django's default would email server errors
# to admins, and this app sends no email.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        # Replaces Django's own handlers, so every message reaches the console once.
        "django": {"handlers": [], "level": "WARNING"},
        # "Not Found" (404) is a warning and mostly bots trying addresses; 500 errors are still logged.
        "django.request": {"level": "ERROR"},
        # runserver's line per request (local only; Gunicorn does not use it).
        "django.server": {"level": "INFO", "propagate": True},
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
