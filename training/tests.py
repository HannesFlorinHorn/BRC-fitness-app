from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from training import methode
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
def pushups(arms):
    return Exercise.objects.create(name="Push-ups", category=arms)


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
    later_session = Session.objects.create(athlete=athlete, finished_at=timezone.now())
    later = SessionExercise.objects.create(session=later_session, exercise=squat, order=1)
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
def test_open_session_finishes_itself_after_26_hours_with_a_3_hour_length(athlete, pushups):
    session = start_session(athlete)
    add_set(add_exercise(session, pushups), Decimal("0"), 20)
    started = timezone.now() - timedelta(hours=25, minutes=59)
    Session.objects.filter(pk=session.pk).update(created_at=started)
    assert get_open_session(athlete) == session

    started = timezone.now() - timedelta(hours=26, minutes=1)
    Session.objects.filter(pk=session.pk).update(created_at=started)
    assert get_open_session(athlete) is None

    session.refresh_from_db()
    assert session.finished_at == started + timedelta(hours=3)
    assert session.exercises.get().sets.count() == 1


@pytest.mark.django_db
def test_finishing_a_session_with_nothing_logged_discards_it(athlete, leg_plan):
    session = start_session(athlete, leg_plan)
    finish_session(session)
    assert not Session.objects.filter(athlete=athlete).exists()


@pytest.mark.django_db
def test_sets_are_numbered_and_last_one_can_be_deleted(athlete, pushups):
    logged = add_exercise(start_session(athlete), pushups)
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
def test_each_exercise_is_in_a_session_once(athlete, squat, leg_plan):
    session = start_session(athlete, leg_plan)
    with pytest.raises(ValueError):
        add_exercise(session, squat)
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionExercise.objects.create(session=session, exercise=squat, order=9)
    assert session.exercises.filter(exercise=squat).count() == 1


@pytest.mark.django_db
def test_exercise_listed_twice_in_a_plan_is_loaded_once(athlete, squat, curl, leg_plan):
    PlanExercise.objects.create(plan=leg_plan, exercise=curl, position=3)
    PlanExercise.objects.create(plan=leg_plan, exercise=squat, position=4)
    session = start_session(athlete, leg_plan)
    assert exercise_names(session) == ["Back squat", "Lunge", "Biceps curl"]
    assert [se.order for se in session.exercises.all()] == [1, 2, 3]


@pytest.mark.django_db
def test_move_exercise_stops_at_the_ends(athlete, leg_plan):
    session = start_session(athlete, leg_plan)
    first = session.exercises.first()

    move_exercise(first, -1)
    assert exercise_names(session) == ["Back squat", "Lunge"]
    move_exercise(first, 1)
    assert exercise_names(session) == ["Lunge", "Back squat"]


# Methode suggestions (docs/METHODE_RULES.md)


def sets(*pairs):
    return [(Decimal(str(weight)), reps) for weight, reps in pairs]


def warmed_up(set_3, set_4=None):
    """A Methode 1 session: warm-ups from the Set 3 weight, then Sets 3 and 4."""
    logged = methode.warm_ups(Decimal(str(set_3[0]))) + sets(set_3)
    return logged + sets(set_4) if set_4 else logged


@pytest.mark.parametrize(
    "reps, table_a, table_b",
    [(0, -2.5, -2.5), (2, -2.5, -2.5), (3, 0, 0), (4, 0, 0), (5, 0, 2.5), (6, 0, 2.5),
     (7, 2.5, 2.5), (10, 2.5, 2.5), (11, 5, 5), (20, 5, 5)],
)
def test_tables_suggest_the_smaller_change_of_each_range(reps, table_a, table_b):
    assert methode.look_up(methode.TABLE_A, reps).change == Decimal(str(table_a))
    assert methode.look_up(methode.TABLE_B, reps).change == Decimal(str(table_b))


def test_weights_round_down_to_plate_steps():
    assert methode.warm_ups(Decimal("27.5")) == [(Decimal("12.5"), 10), (Decimal("20"), 5)]
    assert methode.round_down(Decimal("1")) == 0
    assert methode.round_down(Decimal("-2.5")) == 0


@pytest.mark.parametrize(
    "set_3, set_4, sheet, app",
    [((20, 9), (25, 5), 30, 27.5), ((20, 6), (20, 4), 20, 20), ((20, 5), (20, 2), 17.5, 17.5)],
)
def test_method_1_next_working_weight_follows_the_sheet_examples(set_3, set_4, sheet, app):
    weight, _ = methode.method_1_working_weight(warmed_up(set_3, set_4))
    assert weight == Decimal(str(app))
    # The sheet sometimes takes the upper end of the range; it must stay within it.
    step = methode.look_up(methode.TABLE_B, set_4[1])
    ends = sorted(Decimal(str(set_4[0])) + change for change in (step.change, step.up_to))
    assert ends[0] <= Decimal(str(sheet)) <= ends[1]


def test_method_1_without_set_4_keeps_the_set_3_weight():
    assert methode.method_1_working_weight(warmed_up((60, 8)))[0] == 60


def test_method_1_first_time_explains_the_sets():
    guide = methode.method_1_guide([], [])
    assert guide.lines == methode.METHOD_1_INTRO
    assert guide.next.number == 3 and guide.weight is None and guide.reps is None


def test_method_1_guide_through_a_session():
    history = [warmed_up((60, 6), (62.5, 5))]

    guide = methode.method_1_guide(history, [])
    assert guide.lines == ["Last time: Set 3 · 60 kg × 6 · Set 4 · 62.5 kg × 5",
                           "Today's working weight: 65 kg (+2.5 kg, up to +5 kg)"]
    assert [(s.number, s.weight, s.reps) for s in guide.planned[:3]] == [
        (1, Decimal("32.5"), 10), (2, Decimal("47.5"), 5), (3, Decimal("65"), None)]
    assert (guide.next.number, guide.weight, guide.reps) == (3, Decimal("65"), None)

    today = warmed_up((65, 8))
    guide = methode.method_1_guide(history, today)
    assert guide.lines[-1] == "Set 3: 8 reps → Set 4: 67.5 kg (+2.5 kg, up to +5 kg)"
    assert (guide.next.number, guide.weight) == (4, Decimal("67.5"))

    guide = methode.method_1_guide(history, today + sets((67.5, 3)))
    assert guide.lines[-2:] == ["Set 4: 3 reps → Set 5 (optional): 67.5 kg (same, up to −2.5 kg)",
                                "Next session: Set 3 at 67.5 kg (same)"]

    # After the optional Set 5 the form just repeats the last set.
    guide = methode.method_1_guide(history, today + sets((67.5, 3), (67.5, 3)))
    assert guide.next is None and (guide.weight, guide.reps) == (Decimal("67.5"), 3)


def test_method_2_follows_the_sheet_example():
    # Sessions 1-7 of the sheet's example; the app raises by +2.5 kg (lower end) instead of +5.
    history = [sets((25, 10), (25, 10), (25, 10)), sets((25, 13), (25, 13), (25, 13)),
               sets((25, 15), (25, 15), (25, 15)), sets((27.5, 10), (27.5, 10), (27.5, 10)),
               sets((27.5, 13), (27.5, 13), (27.5, 13)), sets((27.5, 15), (27.5, 13), (27.5, 10)),
               sets((27.5, 15), (27.5, 15), (27.5, 15))]
    targets = [(methode.method_2_state(history[:n]).target, methode.method_2_state(history[:n]).weight)
               for n in range(1, len(history) + 1)]
    assert targets == [(13, 25), (15, 25), (10, Decimal("27.5")), (13, Decimal("27.5")),
                       (15, Decimal("27.5")), (15, Decimal("27.5")), (10, 30)]


def test_method_2_guide():
    assert methode.method_2_guide([], []).lines == ["No sessions yet: 3 sets × 10 reps at a moderate weight."]
    assert methode.method_2_guide([], []).reps == 10

    history = [sets((30, 10), (30, 10), (30, 10)), sets((30, 13), (30, 13), (30, 13)),
               sets((30, 15), (30, 13), (30, 10))]
    guide = methode.method_2_guide(history, [])
    assert guide.lines == ["Last time: 30 kg · 15 / 13 / 10 (target 15 not reached)",
                           "Today: 3 sets × 15 reps at 30 kg"]
    assert [(s.number, s.weight, s.reps) for s in guide.planned] == [(1, 30, 15), (2, 30, 15), (3, 30, 15)]

    guide = methode.method_2_guide(history, sets((30, 15), (30, 15), (30, 15)))
    assert guide.lines[-1] == "Next session: 3 × 10 reps at 32.5 kg"
    assert guide.next is None


@pytest.mark.django_db
def test_method_1_working_set_brings_its_warm_ups(athlete, squat, pushups):
    logged = add_exercise(start_session(athlete), squat)
    add_set(logged, Decimal("60"), 6)
    add_set(logged, Decimal("62.5"), 5)
    assert [(s.number, s.weight_display, s.reps) for s in logged.sets.all()] == [
        (1, "30", 10), (2, "45", 5), (3, "60", 6), (4, "62.5", 5)]

    # Other exercises start at Set 1 as before.
    plain = add_exercise(logged.session, pushups)
    add_set(plain, Decimal("0"), 20)
    assert [s.number for s in plain.sets.all()] == [1]
