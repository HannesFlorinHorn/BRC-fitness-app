import pytest

from accounts.models import User
from training.models import Category, Exercise, Session, SessionExercise


@pytest.fixture
def athlete():
    return User.objects.create_user(email="a@example.com", password="pw")


@pytest.fixture
def squat():
    return Exercise.objects.create(
        name="Back squat", category=Category.objects.get(name="legs"), method=Exercise.Method.METHOD_1
    )


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
