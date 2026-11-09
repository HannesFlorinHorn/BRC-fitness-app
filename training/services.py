"""Session logging steps that touch several models.

Callers pass objects already scoped to the logged-in athlete; these
functions never look anything up by id.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import methode
from .models import Exercise, ExerciseSet, Session, SessionExercise

# Athletes forget to tap Finish; an open session ends by itself after this long.
AUTO_FINISH_AFTER = timedelta(hours=26)
# The real end time is unknown then, so it is recorded as a typical session length.
AUTO_FINISH_DURATION = timedelta(hours=3)


@transaction.atomic
def start_session(athlete, plan=None, date=None):
    """Create a session, preloaded with the plan's active exercises in plan
    order. Without a plan (free training) it starts empty. The date defaults
    to today; a past date logs a session that was already done.

    The plan must come from Plan.objects.visible_to(athlete). Raises
    IntegrityError if the athlete already has an open session."""
    session = Session.objects.create(athlete=athlete, date=date or timezone.localdate())
    if plan is not None:
        entries = plan.plan_exercises.filter(exercise__is_active=True).select_related("exercise")
        # An exercise listed twice in a plan is loaded once, at its first position.
        exercises = list(dict.fromkeys(entry.exercise for entry in entries.order_by("position")))
        for order, exercise in enumerate(exercises, start=1):
            SessionExercise.objects.create(session=session, exercise=exercise, order=order)
    return session


@transaction.atomic
def add_exercise(session, exercise):
    """Append an exercise (from any plan) to the end of the session. Each
    exercise can be in a session once; raises ValueError if it already is."""
    if session.exercises.filter(exercise=exercise).exists():
        raise ValueError(f"{exercise} is already in this session")
    last = session.exercises.order_by("-order").first()
    return SessionExercise.objects.create(
        session=session, exercise=exercise, order=last.order + 1 if last else 1
    )


def move_exercise(session_exercise, offset):
    """Swap with the previous (offset -1) or next (offset 1) exercise of the session."""
    others = session_exercise.session.exercises
    if offset < 0:
        neighbour = others.filter(order__lt=session_exercise.order).order_by("-order").first()
    else:
        neighbour = others.filter(order__gt=session_exercise.order).order_by("order").first()
    if neighbour is not None:
        session_exercise.swap_order_with(neighbour)


@transaction.atomic
def add_set(session_exercise, weight_kg, reps):
    """Log the next set. For Methode 1 with an earlier session, the athlete's
    first entry is the working set (Set 3); the two warm-ups are logged before
    it, worked out from its weight. The first time, the athlete logs them.
    For Methode 2 the first set also stores the plan of the day."""
    if session_exercise.exercise.tracking != Exercise.Tracking.SETS:
        raise ValueError("Tick-when-done exercises have no sets")
    last = session_exercise.sets.order_by("-number").first()
    number = last.number + 1 if last else 1
    if last is None and methode.logs_warm_ups_itself(session_exercise):
        for number, (warm_up_weight, warm_up_reps) in enumerate(methode.warm_ups(weight_kg), start=1):
            ExerciseSet.objects.create(
                session_exercise=session_exercise, number=number, weight_kg=warm_up_weight, reps=warm_up_reps
            )
        number += 1
    if last is None and session_exercise.method == Exercise.Method.METHOD_2:
        # Remember today's plan; the next session is worked out from it.
        plan = methode.method_2_plan_to_store(session_exercise)
        session_exercise.target_reps, session_exercise.target_weight = plan.target, plan.weight
        session_exercise.save(update_fields=["target_reps", "target_weight"])
    return ExerciseSet.objects.create(session_exercise=session_exercise, number=number, weight_kg=weight_kg, reps=reps)


def delete_last_set(session_exercise):
    last = session_exercise.sets.order_by("-number").first()
    if last is not None:
        last.delete()


def mark_done(session_exercise, done=True):
    """Tick (or untick) an exercise that is tracked as "tick when done"."""
    if session_exercise.exercise.tracking != Exercise.Tracking.CHECK:
        raise ValueError("Only tick-when-done exercises can be marked done")
    session_exercise.is_done = done
    session_exercise.save(update_fields=["is_done"])


@transaction.atomic
def finish_session(session, finished_at=None):
    """Drop preloaded exercises the athlete skipped (no sets and not ticked),
    then mark the session done. A session with nothing logged is discarded."""
    session.exercises.filter(sets__isnull=True, is_done=False).delete()
    if not session.exercises.exists() and not session.notes:
        session.delete()
        return
    session.finished_at = finished_at or timezone.now()
    session.save(update_fields=["finished_at"])


def get_open_session(athlete):
    """The athlete's running session, if any. There is no background job, so
    sessions past the time limit are finished here, on the next visit."""
    open_sessions = Session.objects.filter(athlete=athlete, finished_at__isnull=True)
    for session in open_sessions.filter(created_at__lte=timezone.now() - AUTO_FINISH_AFTER):
        finish_session(session, finished_at=session.created_at + AUTO_FINISH_DURATION)
    return open_sessions.first()
