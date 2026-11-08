from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session as LoginSession
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

THIRTY_MINUTES = 30 * 60
SEVEN_DAYS = 7 * 24 * 60 * 60


def log_in(client, **extra):
    User.objects.create_user(email="u@example.com", password="pw", **extra)
    return client.post(reverse("login"), {"username": "u@example.com", "password": "pw"})


@pytest.mark.django_db
@pytest.mark.parametrize("is_staff, age", [(False, SEVEN_DAYS), (True, THIRTY_MINUTES)])
def test_login_lasts_seven_days_for_athletes_and_30_minutes_for_staff(client, is_staff, age):
    response = log_in(client, is_staff=is_staff)
    assert response.cookies["sessionid"]["max-age"] == age

    # Every request restarts the timer.
    response = client.get(reverse("training:history"))
    assert response.cookies["sessionid"]["max-age"] == age


@pytest.mark.django_db
def test_idle_staff_session_is_logged_out(client):
    log_in(client, is_staff=True)
    LoginSession.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    response = client.get(reverse("training:history"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))
