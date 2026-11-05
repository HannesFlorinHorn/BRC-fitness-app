from decimal import Decimal

import pytest
from django.urls import reverse

from accounts.models import User
from training.models import Exercise
from training.services import add_exercise, add_set, finish_session, start_session


@pytest.fixture
def athlete_a():
    return User.objects.create_user(email="a@example.com", password="pw")


@pytest.fixture
def athlete_b():
    return User.objects.create_user(email="b@example.com", password="pw")


@pytest.fixture
def client_a(client, athlete_a):
    client.force_login(athlete_a)
    return client


@pytest.fixture
def squats():
    return Exercise.objects.get(name="Squats")


def logged_session(athlete, exercise, finish=True):
    session = start_session(athlete)
    add_set(add_exercise(session, exercise), Decimal("62.5"), 8)
    if finish:
        finish_session(session)
    return session


@pytest.mark.django_db
def test_everything_requires_login(client):
    response = client.get(reverse("training:history"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("login"))


@pytest.mark.django_db
def test_login_with_email_and_logout(client, athlete_a):
    response = client.post(reverse("login"), {"username": "a@example.com", "password": "pw"})
    assert response.status_code == 302
    assert client.get(reverse("training:history")).status_code == 200

    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("training:history")).status_code == 302


@pytest.mark.django_db
def test_wrong_password_shows_an_error(client, athlete_a):
    response = client.post(reverse("login"), {"username": "a@example.com", "password": "nope"})
    assert b"Email or password is wrong" in response.content


@pytest.mark.django_db
def test_history_shows_own_sessions_and_detail(client_a, athlete_a, squats):
    session = logged_session(athlete_a, squats)

    history = client_a.get(reverse("training:history")).content.decode()
    assert "Legs" in history and "1 exercise · 1 set" in history

    detail = client_a.get(reverse("training:session_detail", args=[session.pk])).content.decode()
    assert "Squats" in detail and "62.5 kg" in detail


@pytest.mark.django_db
def test_athlete_cannot_see_another_athletes_sessions(client_a, athlete_b, squats):
    theirs = logged_session(athlete_b, squats)

    assert b"Legs" not in client_a.get(reverse("training:history")).content
    assert client_a.get(reverse("training:session_detail", args=[theirs.pk])).status_code == 404
