"""Gunicorn settings for production. Start with: gunicorn -c config/gunicorn.conf.py"""

import os

wsgi_app = "config.wsgi:application"

# Caddy reaches Gunicorn inside Docker; the port is never published to the outside.
bind = "0.0.0.0:8000"
# Two are plenty for about 10 people, and SQLite takes one writer at a time anyway.
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
# A stuck request gets its worker restarted instead of blocking it for good.
timeout = 30
# On a restart, requests already running (a set being saved) get this long to finish.
graceful_timeout = 30
# Restart each worker now and then (spread out), so a slow memory leak never builds up.
max_requests = 1000
max_requests_jitter = 100

# Errors go to the console (docker compose logs). Caddy already logs every request.
errorlog = "-"
accesslog = None

# forwarded_allow_ips is left at its default on purpose: Django reads Caddy's
# X-Forwarded-Proto itself (SECURE_PROXY_SSL_HEADER), whatever Gunicorn trusts.
# What keeps that header honest is that Caddy is the only way in.
