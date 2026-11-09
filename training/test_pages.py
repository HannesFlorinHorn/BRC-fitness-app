from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from training.models import Category, Exercise, Plan, Session
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
    # No Methode, so tests about other topics get no warm-ups or suggestions.
    return Exercise.objects.create(name="Box squats", category=Category.objects.get(name="legs"))


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
    assert "Box squats" in detail and "62.5 kg" in detail


@pytest.mark.django_db
def test_history_lists_newest_sessions_first(client_a, athlete_a, squats):
    today = timezone.localdate()
    sessions = []
    for days_ago in (1, 0, 3):
        session = start_session(athlete_a, date=today - timedelta(days=days_ago))
        add_set(add_exercise(session, squats), Decimal("60"), 8)
        finish_session(session)
        sessions.append(session)

    page = client_a.get(reverse("training:history")).content.decode()
    positions = [page.index(reverse("training:session_detail", args=[s.pk])) for s in sessions]
    assert positions[1] < positions[0] < positions[2]


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

    # Squats is Methode 1 and never logged before: the athlete logs the
    # warm-ups too (with the comma a German phone keyboard types).
    squats = session.exercises.get(exercise__name="Squats")
    sets_url = reverse("training:exercise_sets", args=[squats.pk])
    page = client_a.get(sets_url).content.decode()
    assert "No sessions yet:" in page and "Set 1 · warm-up" in page and "Save Set 1" in page and 'value="10"' in page
    client_a.post(sets_url, {"weight_kg": "30", "reps": "10"})
    client_a.post(sets_url, {"weight_kg": "45", "reps": "5"})
    assert client_a.post(sets_url, {"weight_kg": "62,5", "reps": "8"}).status_code == 302
    assert [(s.weight_display, s.reps) for s in squats.sets.all()] == [("30", 10), ("45", 5), ("62.5", 8)]

    # Set 4 is suggested from the Set 3 reps (Table A: 8 reps, +2.5 kg).
    page = client_a.get(sets_url).content.decode()
    assert "Set 3: 8 reps → Set 4: 65 kg" in page and 'value="65"' in page
    client_a.post(sets_url, {"weight_kg": "65", "reps": "6"})
    assert "Next session: Set 3 at 67.5 kg" in client_a.get(sets_url).content.decode()
    client_a.post(sets_url, {"weight_kg": "99", "reps": "1"})

    # A typo is removed again.
    client_a.post(reverse("training:set_delete_last", args=[squats.pk]))
    assert [s.reps for s in squats.sets.all()] == [10, 5, 8, 6]

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
    assert "3 exercises · 5 sets" in client_a.get(reverse("training:history")).content.decode()


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
def test_exercise_picker_hides_exercises_already_in_the_session(client_a, athlete_a, plan):
    squats = Exercise.objects.get(name="Squats")
    session = start_session(athlete_a, plan)
    url = reverse("training:exercise_add", args=[session.pk])
    page = client_a.get(url).content.decode()
    assert "Squats" not in page and "Leg curl" in page

    # A stale page or a double tap posts it anyway: no duplicate, just a note.
    response = client_a.post(url, {"exercise": squats.pk}, follow=True)
    assert session.exercises.filter(exercise=squats).count() == 1
    assert "Squats is already in this session." in response.content.decode()


@pytest.mark.django_db
def test_adding_an_unknown_exercise_is_a_404(client_a, athlete_a):
    url = reverse("training:exercise_add", args=[start_session(athlete_a).pk])
    assert client_a.post(url, {"exercise": "abc"}).status_code == 404
    assert client_a.post(url, {"exercise": "999999"}).status_code == 404


@pytest.mark.django_db
def test_missing_and_foreign_pages_show_the_friendly_404(client_a, athlete_b, squats):
    theirs = logged_session(athlete_b, squats)
    for url in ("/no-such-page/", reverse("training:session_detail", args=[theirs.pk])):
        response = client_a.get(url)
        assert response.status_code == 404
        page = response.content.decode()
        assert "Page not found" in page and "Back to history" in page
        assert "Legs" not in page


@pytest.mark.django_db
def test_staff_on_athlete_pages_see_the_friendly_403(client):
    client.force_login(User.objects.create_user(email="coach@example.com", password="pw", is_staff=True))
    response = client.get(reverse("training:start"))
    assert response.status_code == 403
    assert "Log in with your athlete account" in response.content.decode()


@pytest.mark.django_db
def test_expired_form_shows_the_page_expired_message(athlete_a):
    client = Client(enforce_csrf_checks=True)
    client.force_login(athlete_a)
    response = client.post(reverse("training:start"), {"date": timezone.localdate().isoformat(), "plan": ""})
    assert response.status_code == 403
    assert "This page has expired" in response.content.decode()
    assert not Session.objects.exists()


def test_server_error_page_renders_without_a_request():
    page = render_to_string("500.html")
    assert "Something went wrong" in page and reverse("training:history") in page


@pytest.mark.django_db
def test_opening_an_action_address_goes_back_to_the_log(client_a, athlete_a, plan):
    session = start_session(athlete_a, plan)
    squats = session.exercises.get(exercise__name="Squats")
    add_set(squats, Decimal("60"), 8)
    logged_sets = squats.sets.count()
    planks = session.exercises.get(exercise__name="Planks")
    log_url = reverse("training:session_log", args=[session.pk])

    for url in (
        reverse("training:session_finish", args=[session.pk]),
        reverse("training:set_delete_last", args=[squats.pk]),
        reverse("training:exercise_tick", args=[planks.pk]),
        reverse("training:exercise_move", args=[planks.pk, "up"]),
    ):
        response = client_a.get(url)
        assert response.status_code == 302 and response["Location"] == log_url, url

    session.refresh_from_db()
    planks.refresh_from_db()
    assert session.finished_at is None and squats.sets.count() == logged_sets
    assert not planks.is_done and exercise_order(session)[-1] == "Planks"


@pytest.mark.django_db
def test_opening_logout_directly_keeps_you_logged_in(client_a):
    response = client_a.get(reverse("logout"))
    assert response["Location"] == reverse("training:history")
    assert client_a.get(reverse("training:history")).status_code == 200


def exercise_order(session):
    return [logged.exercise.name for logged in session.exercises.all()]


@pytest.mark.django_db
def test_legal_pages_open_without_login_and_are_linked_from_the_login_page(client):
    login_page = client.get(reverse("login")).content.decode()
    for name, text in (("legal_notice", "Hannes-Florin Horn"), ("privacy", "LDA Brandenburg")):
        assert reverse(name) in login_page
        response = client.get(reverse(name))
        assert response.status_code == 200 and text in response.content.decode()
        assert '<html lang="de"' in response.content.decode()


@pytest.mark.django_db
def test_method_2_page_shows_todays_target(client_a, athlete_a):
    leg_curl = Exercise.objects.get(name="Leg curl")
    earlier = start_session(athlete_a, date=timezone.localdate() - timedelta(days=7))
    logged = add_exercise(earlier, leg_curl)
    for _ in range(3):
        add_set(logged, Decimal("30"), 10)
    finish_session(earlier)

    today = add_exercise(start_session(athlete_a), leg_curl)
    page = client_a.get(reverse("training:exercise_sets", args=[today.pk])).content.decode()
    # The earlier session was the first one: its weight with 10+ reps, target 10.
    assert "Last time: 30 kg · 10 / 10 / 10 (first session)" in page
    assert "Today: 3 sets × 10 reps at 30 kg" in page
    assert 'value="30"' in page and 'value="10"' in page


@pytest.mark.django_db
def test_exercise_without_methode_repeats_the_last_set(client_a, athlete_a, squats):
    logged = add_exercise(start_session(athlete_a), squats)
    add_set(logged, Decimal("40"), 12)
    page = client_a.get(reverse("training:exercise_sets", args=[logged.pk])).content.decode()
    assert 'value="40"' in page and 'value="12"' in page
    assert 'class="message"' not in page and "next-set" not in page and "Save set" in page


@pytest.mark.django_db
def test_session_log_greys_out_done_exercises(client_a, athlete_a, squats):
    session = start_session(athlete_a)
    leg_curl = add_exercise(session, Exercise.objects.get(name="Leg curl"))  # Methode 2
    for _ in range(3):
        add_set(leg_curl, Decimal("30"), 10)
    open_one = add_exercise(session, squats)
    add_set(open_one, Decimal("40"), 8)

    page = client_a.get(reverse("training:session_log", args=[session.pk])).content.decode()
    assert page.count('class="grow exercise-link done"') == 1
    assert page.count('class="grow exercise-link"') == 1
