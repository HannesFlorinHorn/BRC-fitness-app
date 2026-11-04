from decimal import Decimal

import pytest

from accounts.models import User
from training.models import Category, Exercise, ExerciseSet, Session, SessionExercise
from training.services import add_exercise, finish_session, start_session


@pytest.fixture
def athlete():
    return User.objects.create_user(email="a@example.com", password="pw")


@pytest.fixture
def legs():
    return Category.objects.get(name="legs")


@pytest.fixture
def arms():
    return Category.objects.get(name="arms")


@pytest.fixture
def squat(legs):
    return Exercise.objects.create(name="Back squat", category=legs, method=1, position=1)


@pytest.fixture
def lunge(legs):
    return Exercise.objects.create(name="Lunge", category=legs, method=2, position=2)


@pytest.fixture
def curl(arms):
    return Exercise.objects.create(name="Biceps curl", category=arms, method=1, position=1)


def exercise_names(session):
    return [se.exercise.name for se in session.exercises.all()]


@pytest.mark.django_db
def test_session_exercise_keeps_method_when_catalog_changes(athlete, squat):
    session = Session.objects.create(athlete=athlete)
    logged = SessionExercise.objects.create(session=session, exercise=squat, order=1)
    assert logged.method == Exercise.Method.METHOD_1

    squat.method = Exercise.Method.METHOD_2
    squat.save()

    logged.refresh_from_db()
    assert logged.method == Exercise.Method.METHOD_1
    later = SessionExercise.objects.create(session=session, exercise=squat, order=2)
    assert later.method == Exercise.Method.METHOD_2


@pytest.mark.django_db
def test_start_session_preloads_active_plan_exercises_in_template_order(athlete, legs, squat, lunge):
    Exercise.objects.create(name="Leg press", category=legs, method=1, position=0, is_active=False)
    squat.position = 3
    squat.save()

    session = start_session(athlete, legs)

    assert exercise_names(session) == ["Lunge", "Back squat"]
    assert [se.order for se in session.exercises.all()] == [1, 2]


@pytest.mark.django_db
def test_mixed_session_starts_empty_and_takes_exercises_from_any_plan(athlete, squat, curl):
    session = start_session(athlete)
    assert session.label == "Session"

    add_exercise(session, curl)
    add_exercise(session, squat)

    assert exercise_names(session) == ["Biceps curl", "Back squat"]
    assert session.label == "Arms · Legs"


@pytest.mark.django_db
def test_swap_order_within_session(athlete, legs, squat, lunge):
    session = start_session(athlete, legs)
    first, second = session.exercises.all()

    first.swap_order_with(second)

    assert exercise_names(session) == ["Lunge", "Back squat"]


@pytest.mark.django_db
def test_cannot_swap_with_exercise_of_another_session(athlete, legs, squat):
    one = start_session(athlete, legs).exercises.get()
    other = start_session(athlete, legs).exercises.get()

    with pytest.raises(ValueError):
        one.swap_order_with(other)


@pytest.mark.django_db
def test_finish_drops_skipped_exercises_and_label_follows_what_was_done(athlete, legs, squat, lunge, curl):
    session = start_session(athlete, legs)
    done = session.exercises.get(exercise=squat)
    ExerciseSet.objects.create(session_exercise=done, number=1, weight_kg=Decimal("60"), reps=8)
    extra = add_exercise(session, curl)
    ExerciseSet.objects.create(session_exercise=extra, number=1, weight_kg=Decimal("12.5"), reps=10)

    finish_session(session)

    assert session.is_finished
    assert exercise_names(session) == ["Back squat", "Biceps curl"]
    assert session.label == "Legs · Arms"
