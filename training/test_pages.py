from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from training.models import Exercise, Plan, Session
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
def test_email_is_case_insensitive(client):
    user = User.objects.create_user(email="Anna@Club.DE", password="pw")
    assert user.email == "anna@club.de"

    response = client.post(reverse("login"), {"username": "ANNA@club.de", "password": "pw"})
    assert response.status_code == 302

    # The admin refuses a second account that differs only in capitals.
    with pytest.raises(ValidationError):
        User(email="anna@CLUB.de", password="x").full_clean()


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


@pytest.fixture
def plan():
    return Plan.objects.get(name="Legs", owner=None)


def open_session_of(athlete):
    return Session.objects.get(athlete=athlete, finished_at__isnull=True)


@pytest.mark.django_db
def test_full_logging_flow(client_a, athlete_a, plan):
    today = timezone.localdate().isoformat()

    # Start from the Legs plan: its exercises are preloaded.
    response = client_a.post(reverse("training:start"), {"date": today, "plan": plan.pk})
    session = open_session_of(athlete_a)
    assert response["Location"] == reverse("training:session_log", args=[session.pk])
    page = client_a.get(response["Location"]).content.decode()
    assert "Squats" in page and "Planks" in page

    # First set, with the comma a German phone keyboard types.
    squats = session.exercises.get(exercise__name="Squats")
    sets_url = reverse("training:exercise_sets", args=[squats.pk])
    assert client_a.post(sets_url, {"weight_kg": "62,5", "reps": "8"}).status_code == 302

    # The form comes back prefilled with the previous set.
    page = client_a.get(sets_url).content.decode()
    assert 'value="62.5"' in page and 'value="8"' in page
    client_a.post(sets_url, {"weight_kg": "62.5", "reps": "6"})
    client_a.post(sets_url, {"weight_kg": "99", "reps": "1"})

    # A typo is removed again.
    client_a.post(reverse("training:set_delete_last", args=[squats.pk]))
    assert [s.reps for s in squats.sets.all()] == [8, 6]

    # Tick Planks, add an exercise from another plan, swap the order.
    planks = session.exercises.get(exercise__name="Planks")
    client_a.post(reverse("training:exercise_tick", args=[planks.pk]))
    curl = Exercise.objects.get(name="Leg curl")
    add = client_a.post(reverse("training:exercise_add", args=[session.pk]), {"exercise": curl.pk})
    assert add["Location"] == reverse("training:session_log", args=[session.pk])
    curl_url = reverse("training:exercise_sets", args=[session.exercises.get(exercise=curl).pk])
    client_a.post(curl_url, {"weight_kg": "30", "reps": "12"})
    client_a.post(reverse("training:exercise_move", args=[planks.pk, "up"]))

    # Finish: skipped exercises are gone, the session is in the history.
    response = client_a.post(reverse("training:session_finish", args=[session.pk]), {"notes": "Felt good"})
    assert response["Location"] == reverse("training:session_detail", args=[session.pk])
    detail = client_a.get(response["Location"]).content.decode()
    assert "Felt good" in detail and "Done ✓" in detail and "62.5 kg" in detail
    assert "Romanian deadlift" not in detail
    assert [logged.exercise.name for logged in session.exercises.all()] == ["Squats", "Planks", "Leg curl"]
    assert "3 exercises · 3 sets" in client_a.get(reverse("training:history")).content.decode()


@pytest.mark.django_db
def test_start_page_prefills_today_and_accepts_past_but_not_future_dates(client_a, athlete_a):
    today = timezone.localdate()
    assert f'value="{today.isoformat()}"'.encode() in client_a.get(reverse("training:start")).content

    future = (today + timedelta(days=1)).isoformat()
    response = client_a.post(reverse("training:start"), {"date": future, "plan": ""})
    assert b"cannot be in the future" in response.content
    assert not Session.objects.exists()

    past = today - timedelta(days=3)
    client_a.post(reverse("training:start"), {"date": past.isoformat(), "plan": ""})
    assert open_session_of(athlete_a).date == past


@pytest.mark.django_db
def test_start_goes_to_the_open_session_instead_of_a_second_one(client_a, athlete_a):
    session = start_session(athlete_a)
    url = reverse("training:session_log", args=[session.pk])

    assert client_a.get(reverse("training:start"))["Location"] == url
    today = timezone.localdate().isoformat()
    assert client_a.post(reverse("training:start"), {"date": today, "plan": ""})["Location"] == url
    assert Session.objects.count() == 1


@pytest.mark.django_db
def test_finishing_an_empty_session_discards_it(client_a, athlete_a, plan):
    session = start_session(athlete_a, plan)
    response = client_a.post(reverse("training:session_finish", args=[session.pk]), {"notes": ""}, follow=True)
    assert b"discarded" in response.content
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_invalid_set_shows_an_error_and_saves_nothing(client_a, athlete_a, squats):
    logged = add_exercise(start_session(athlete_a), squats)
    url = reverse("training:exercise_sets", args=[logged.pk])
    for data in ({"weight_kg": "-5", "reps": "8"}, {"weight_kg": "60", "reps": "0"}, {"weight_kg": "abc", "reps": "8"}):
        assert client_a.post(url, data).status_code == 200
    assert not logged.sets.exists()


@pytest.mark.django_db
def test_finished_session_cannot_be_changed(client_a, athlete_a, squats):
    session = logged_session(athlete_a, squats)
    logged = session.exercises.get()

    client_a.post(reverse("training:exercise_sets", args=[logged.pk]), {"weight_kg": "1", "reps": "1"})
    client_a.post(reverse("training:set_delete_last", args=[logged.pk]))

    assert logged.sets.count() == 1
    assert logged.sets.get().reps == 8


@pytest.mark.django_db
def test_session_past_the_time_limit_stops_accepting_sets(client_a, athlete_a, squats):
    session = logged_session(athlete_a, squats, finish=False)
    Session.objects.filter(pk=session.pk).update(created_at=timezone.now() - timedelta(hours=27))
    logged = session.exercises.get()

    response = client_a.post(reverse("training:exercise_sets", args=[logged.pk]), {"weight_kg": "1", "reps": "1"})

    assert response["Location"] == reverse("training:session_detail", args=[session.pk])
    assert logged.sets.count() == 1


@pytest.mark.django_db
def test_athlete_cannot_touch_another_athletes_open_session(client_a, athlete_b, squats):
    session = logged_session(athlete_b, squats, finish=False)
    logged = session.exercises.get()
    pk = session.pk

    for url in (
        reverse("training:session_detail", args=[pk]),
        reverse("training:session_log", args=[pk]),
        reverse("training:exercise_add", args=[pk]),
        reverse("training:exercise_sets", args=[logged.pk]),
    ):
        assert client_a.get(url).status_code == 404, url

    for url, data in (
        (reverse("training:exercise_sets", args=[logged.pk]), {"weight_kg": "1", "reps": "1"}),
        (reverse("training:exercise_add", args=[pk]), {"exercise": squats.pk}),
        (reverse("training:set_delete_last", args=[logged.pk]), {}),
        (reverse("training:exercise_tick", args=[logged.pk]), {}),
        (reverse("training:exercise_move", args=[logged.pk, "up"]), {}),
        (reverse("training:session_finish", args=[pk]), {"notes": "hacked"}),
    ):
        assert client_a.post(url, data).status_code == 404, url

    session.refresh_from_db()
    assert session.finished_at is None and session.notes == ""
    assert session.exercises.count() == 1
    assert [(s.weight_display, s.reps) for s in logged.sets.all()] == [("62.5", 8)]


@pytest.mark.django_db
def test_athlete_cannot_start_a_session_from_another_athletes_plan(client_a, athlete_a, athlete_b):
    theirs = Plan.objects.create(name="Private", owner=athlete_b)

    assert b"Private" not in client_a.get(reverse("training:start")).content
    today = timezone.localdate().isoformat()
    client_a.post(reverse("training:start"), {"date": today, "plan": theirs.pk})
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_staff_accounts_cannot_log_sessions(client, athlete_b, squats):
    client.force_login(User.objects.create_user(email="coach@example.com", password="pw", is_staff=True))
    session = logged_session(athlete_b, squats, finish=False)

    assert client.get(reverse("training:history")).status_code == 200
    assert client.get(reverse("training:start")).status_code == 403
    today = timezone.localdate().isoformat()
    assert client.post(reverse("training:start"), {"date": today, "plan": ""}).status_code == 403
    url = reverse("training:exercise_sets", args=[session.exercises.get().pk])
    assert client.post(url, {"weight_kg": "1", "reps": "1"}).status_code == 403


@pytest.mark.django_db
def test_adding_an_unknown_exercise_is_a_404(client_a, athlete_a):
    url = reverse("training:exercise_add", args=[start_session(athlete_a).pk])
    assert client_a.post(url, {"exercise": "abc"}).status_code == 404
    assert client_a.post(url, {"exercise": "999999"}).status_code == 404
