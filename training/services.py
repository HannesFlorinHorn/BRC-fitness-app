"""Session logging steps that touch several models.

Callers pass objects already scoped to the logged-in athlete; these
functions never look anything up by id.
"""

from django.db import transaction
from django.utils import timezone

from .models import Exercise, Session, SessionExercise


@transaction.atomic
def start_session(athlete, plan=None):
    """Create a session, preloaded with the plan's active exercises in plan
    order. Without a plan (free training) it starts empty.

    The plan must come from Plan.objects.visible_to(athlete)."""
    session = Session.objects.create(athlete=athlete)
    if plan is not None:
        entries = plan.plan_exercises.filter(exercise__is_active=True).select_related("exercise")
        for order, entry in enumerate(entries.order_by("position"), start=1):
            SessionExercise.objects.create(session=session, exercise=entry.exercise, order=order)
    return session


def add_exercise(session, exercise):
    """Append an exercise (from any plan) to the end of the session."""
    last = session.exercises.order_by("-order").first()
    return SessionExercise.objects.create(
        session=session, exercise=exercise, order=last.order + 1 if last else 1
    )


def mark_done(session_exercise, done=True):
    """Tick (or untick) an exercise that is tracked as "tick when done"."""
    if session_exercise.exercise.tracking != Exercise.Tracking.CHECK:
        raise ValueError("Only tick-when-done exercises can be marked done")
    session_exercise.is_done = done
    session_exercise.save(update_fields=["is_done"])


@transaction.atomic
def finish_session(session):
    """Drop preloaded exercises the athlete skipped (no sets and not ticked),
    then mark the session done."""
    session.exercises.filter(sets__isnull=True, is_done=False).delete()
    session.finished_at = timezone.now()
    session.save(update_fields=["finished_at"])
