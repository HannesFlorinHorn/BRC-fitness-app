"""Session logging steps that touch several models.

Callers pass objects already scoped to the logged-in athlete; these
functions never look anything up by id.
"""

from django.db import transaction
from django.utils import timezone

from .models import Exercise, Session, SessionExercise


@transaction.atomic
def start_session(athlete, plan=None):
    """Create a session, preloaded with the plan's active exercises in
    template order. Without a plan (mixed training) it starts empty."""
    session = Session.objects.create(athlete=athlete)
    if plan is not None:
        exercises = Exercise.objects.filter(category=plan, is_active=True).order_by("position", "name")
        for order, exercise in enumerate(exercises, start=1):
            SessionExercise.objects.create(session=session, exercise=exercise, order=order)
    return session


def add_exercise(session, exercise):
    """Append an exercise (from any plan) to the end of the session."""
    last = session.exercises.order_by("-order").first()
    return SessionExercise.objects.create(
        session=session, exercise=exercise, order=last.order + 1 if last else 1
    )


@transaction.atomic
def finish_session(session):
    """Drop preloaded exercises the athlete skipped, then mark the session done."""
    session.exercises.filter(sets__isnull=True).delete()
    session.finished_at = timezone.now()
    session.save(update_fields=["finished_at"])
