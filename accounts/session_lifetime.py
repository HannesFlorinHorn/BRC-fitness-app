"""How long a login lasts without activity.

Admin and app share one session cookie, so the lifetime depends on the
account, not on the page: staff accounts (which can read everyone's data)
time out quickly, athletes stay logged in on their phone. Every request
restarts the timer (SESSION_SAVE_EVERY_REQUEST).
"""

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


def session_age(user):
    return settings.STAFF_SESSION_AGE if user.is_staff else settings.SESSION_COOKIE_AGE


class SessionLifetimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.session.set_expiry(session_age(request.user))
        return self.get_response(request)


@receiver(user_logged_in)
def set_lifetime_at_login(sender, request, user, **kwargs):
    # The middleware ran before the login, so set the lifetime of the new session here.
    request.session.set_expiry(session_age(user))
