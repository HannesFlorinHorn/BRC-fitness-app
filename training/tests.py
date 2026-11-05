from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from training.models import Category, Exercise, ExerciseSet, Plan, PlanExercise, Session, SessionExercise
from training.services import (
    add_exercise,
    add_set,
    delete_last_set,
    finish_session,
    get_open_session,
    mark_done,
    move_exercise,
    start_session,
)


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
    return Exercise.objects.create(name="Back squat", category=legs, method=1)


@pytest.fixture
def lunge(legs):
    return Exercise.objects.create(name="Lunge", category=legs, method=2)


@pytest.fixture
def curl(arms):
    return Exercise.objects.create(name="Biceps curl", category=arms, method=1)


@pytest.fixture
def leg_plan(squat, lunge):
    plan = Plan.objects.create(name="Test legs")
    PlanExercise.objects.create(plan=plan, exercise=squat, position=1)
    PlanExercise.objects.create(plan=plan, exercise=lunge, position=2)
    return plan


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
def test_start_session_preloads_active_plan_exercises_in_plan_order(athlete, legs, leg_plan, squat):
    retired = Exercise.objects.create(name="Leg press", category=legs, method=1, is_active=False)
    PlanExercise.objects.create(plan=leg_plan, exercise=retired, position=0)
    leg_plan.plan_exercises.filter(exercise=squat).update(position=3)

    session = start_session(athlete, leg_plan)

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
def test_swap_order_within_session(athlete, leg_plan):
    session = start_session(athlete, leg_plan)
    first, second = session.exercises.all()

    first.swap_order_with(second)

    assert exercise_names(session) == ["Lunge", "Back squat"]


@pytest.mark.django_db
def test_cannot_swap_with_exercise_of_another_session(athlete, leg_plan):
    one = start_session(athlete, leg_plan).exercises.first()
    other_athlete = User.objects.create_user(email="b@example.com", password="pw")
    other = start_session(other_athlete, leg_plan).exercises.first()

    with pytest.raises(ValueError):
        one.swap_order_with(other)


@pytest.mark.django_db
def test_finish_drops_skipped_exercises_and_label_follows_what_was_done(athlete, leg_plan, squat, curl):
    session = start_session(athlete, leg_plan)
    done = session.exercises.get(exercise=squat)
    ExerciseSet.objects.create(session_exercise=done, number=1, weight_kg=Decimal("60"), reps=8)
    extra = add_exercise(session, curl)
    ExerciseSet.objects.create(session_exercise=extra, number=1, weight_kg=Decimal("12.5"), reps=10)

    finish_session(session)

    assert session.is_finished
    assert exercise_names(session) == ["Back squat", "Biceps curl"]
    assert session.label == "Legs · Arms"


@pytest.mark.django_db
def test_same_exercise_can_be_in_several_plans(athlete, leg_plan, squat, curl):
    own = Plan.objects.create(name="My full body", owner=athlete)
    PlanExercise.objects.create(plan=own, exercise=curl, position=1)
    PlanExercise.objects.create(plan=own, exercise=squat, position=2)

    assert set(squat.plans.all()) == {leg_plan, own}
    assert exercise_names(start_session(athlete, own)) == ["Biceps curl", "Back squat"]


@pytest.mark.django_db
def test_athletes_see_club_plans_and_only_their_own_plans(athlete):
    other = User.objects.create_user(email="b@example.com", password="pw")
    mine = Plan.objects.create(name="Mine", owner=athlete)
    theirs = Plan.objects.create(name="Theirs", owner=other)

    visible = set(Plan.objects.visible_to(athlete).values_list("name", flat=True))
    assert visible == {"Legs", "Arms", "Core", "Mine"}
    assert list(Plan.objects.owned_by(athlete)) == [mine]
    assert theirs not in Plan.objects.visible_to(athlete)


@pytest.mark.django_db
def test_club_plan_names_are_unique_but_athletes_may_reuse_them(athlete):
    Plan.objects.create(name="Legs", owner=athlete)
    with pytest.raises(IntegrityError):
        Plan.objects.create(name="Legs", owner=None)


@pytest.mark.django_db
def test_club_plans_are_seeded_in_order():
    def names(plan_name):
        plan = Plan.objects.get(name=plan_name, owner=None)
        return [entry.exercise.name for entry in plan.plan_exercises.order_by("position")]

    assert names("Legs") == ["Squats", "Romanian deadlift", "Split squats", "Planks"]
    assert names("Arms")[-1] == "Abs"
    assert len(names("Core")) == 5
    assert Exercise.objects.get(name="Planks").method is None


@pytest.mark.django_db
def test_tick_exercises_survive_finish_only_when_ticked(athlete, curl):
    planks = Exercise.objects.create(name="Test planks", category=curl.category, tracking=Exercise.Tracking.CHECK)
    abs_ = Exercise.objects.create(name="Test abs", category=curl.category, tracking=Exercise.Tracking.CHECK)
    session = start_session(athlete)
    mark_done(add_exercise(session, planks))
    add_exercise(session, abs_)

    finish_session(session)

    assert exercise_names(session) == ["Test planks"]
    assert session.exercises.get().method is None


@pytest.mark.django_db
def test_only_tick_exercises_can_be_marked_done(athlete, squat):
    with pytest.raises(ValueError):
        mark_done(add_exercise(start_session(athlete), squat))


@pytest.mark.django_db
def test_only_one_open_session_per_athlete(athlete):
    first = start_session(athlete)
    add_exercise(first, Exercise.objects.get(name="Squats")).sets.create(number=1, weight_kg=60, reps=8)
    with pytest.raises(IntegrityError), transaction.atomic():
        start_session(athlete)

    finish_session(first)
    assert start_session(athlete).date == timezone.localdate()


@pytest.mark.django_db
def test_session_can_be_logged_for_a_past_date(athlete):
    assert start_session(athlete, date=date(2026, 10, 1)).date == date(2026, 10, 1)


@pytest.mark.django_db
def test_open_session_finishes_itself_after_four_hours(athlete, squat):
    session = start_session(athlete)
    add_set(add_exercise(session, squat), Decimal("60"), 8)
    started = timezone.now() - timedelta(hours=3, minutes=59)
    Session.objects.filter(pk=session.pk).update(created_at=started)
    assert get_open_session(athlete) == session

    started = timezone.now() - timedelta(hours=4, minutes=1)
    Session.objects.filter(pk=session.pk).update(created_at=started)
    assert get_open_session(athlete) is None

    session.refresh_from_db()
    assert session.finished_at == started + timedelta(hours=4)
    assert session.exercises.get().sets.count() == 1


@pytest.mark.django_db
def test_finishing_a_session_with_nothing_logged_discards_it(athlete, leg_plan):
    session = start_session(athlete, leg_plan)
    finish_session(session)
    assert not Session.objects.filter(athlete=athlete).exists()


@pytest.mark.django_db
def test_sets_are_numbered_and_last_one_can_be_deleted(athlete, squat):
    logged = add_exercise(start_session(athlete), squat)
    add_set(logged, Decimal("60"), 8)
    add_set(logged, Decimal("62.5"), 6)
    assert [(s.number, s.weight_display) for s in logged.sets.all()] == [(1, "60"), (2, "62.5")]

    delete_last_set(logged)
    assert [s.number for s in logged.sets.all()] == [1]


@pytest.mark.django_db
def test_tick_exercises_take_no_sets(athlete):
    logged = add_exercise(start_session(athlete), Exercise.objects.get(name="Planks"))
    with pytest.raises(ValueError):
        add_set(logged, Decimal("0"), 1)


@pytest.mark.django_db
def test_move_exercise_stops_at_the_ends(athlete, leg_plan):
    session = start_session(athlete, leg_plan)
    first = session.exercises.first()

    move_exercise(first, -1)
    assert exercise_names(session) == ["Back squat", "Lunge"]
    move_exercise(first, 1)
    assert exercise_names(session) == ["Lunge", "Back squat"]
