from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .forms import SetForm, StartSessionForm
from .models import Exercise, Session, SessionExercise


def athlete_only(view):
    """Staff accounts are read-only in athlete pages."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def redirect_to_finished(request, session):
    messages.info(request, "This session is already finished.")
    return redirect("training:session_detail", session.pk)


def with_open_session(view):
    """Pass the athlete's own open session to the view instead of its id."""

    @wraps(view)
    @athlete_only
    def wrapper(request, pk, *args, **kwargs):
        services.get_open_session(request.user)
        session = get_object_or_404(Session, pk=pk, athlete=request.user)
        if session.is_finished:
            return redirect_to_finished(request, session)
        return view(request, session, *args, **kwargs)

    return wrapper


def with_open_exercise(view):
    """Pass the athlete's own logged exercise of an open session to the view."""

    @wraps(view)
    @athlete_only
    def wrapper(request, pk, *args, **kwargs):
        services.get_open_session(request.user)
        logged = get_object_or_404(
            SessionExercise.objects.select_related("session", "exercise"), pk=pk, session__athlete=request.user
        )
        if logged.session.is_finished:
            return redirect_to_finished(request, logged.session)
        return view(request, logged, *args, **kwargs)

    return wrapper


def history(request):
    open_session = services.get_open_session(request.user)
    sessions = (
        Session.objects.filter(athlete=request.user, finished_at__isnull=False)
        .annotate(exercise_count=Count("exercises", distinct=True), set_count=Count("exercises__sets", distinct=True))
        .prefetch_related("exercises__exercise__category")
    )
    return render(request, "training/history.html", {"sessions": sessions, "open_session": open_session})


def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk, athlete=request.user)
    if not session.is_finished:
        return redirect("training:session_log", session.pk)
    exercises = session.exercises.select_related("exercise__category").prefetch_related("sets")
    return render(request, "training/session_detail.html", {"session": session, "exercises": exercises})


@athlete_only
def start(request):
    open_session = services.get_open_session(request.user)
    if open_session is not None:
        return redirect("training:session_log", open_session.pk)

    form = StartSessionForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            session = services.start_session(
                request.user, plan=form.cleaned_data["plan"], date=form.cleaned_data["date"]
            )
        except IntegrityError:
            # A double tap on the button: the first request already started it.
            session = services.get_open_session(request.user)
        return redirect("training:session_log", session.pk)
    return render(request, "training/start.html", {"form": form, "plans": form.fields["plan"].queryset})


@with_open_session
def session_log(request, session):
    exercises = session.exercises.select_related("exercise__category").prefetch_related("sets")
    return render(request, "training/session_log.html", {"session": session, "exercises": exercises})


@with_open_session
def exercise_add(request, session):
    if request.method == "POST":
        try:
            exercise = Exercise.objects.get(pk=request.POST.get("exercise"), is_active=True)
        except (Exercise.DoesNotExist, ValueError):
            raise Http404
        logged = services.add_exercise(session, exercise)
        if exercise.tracking == Exercise.Tracking.CHECK:
            return redirect("training:session_log", session.pk)
        return redirect("training:exercise_sets", logged.pk)
    exercises = Exercise.objects.filter(is_active=True).select_related("category")
    return render(request, "training/exercise_add.html", {"session": session, "exercises": exercises})


@require_POST
@with_open_session
def session_finish(request, session):
    session.notes = request.POST.get("notes", "").strip()
    session.save(update_fields=["notes"])
    services.finish_session(session)
    if session.pk is None:  # finish_session deleted it
        messages.info(request, "Nothing was logged, so the session was discarded.")
        return redirect("training:history")
    return redirect("training:session_detail", session.pk)


@with_open_exercise
def exercise_sets(request, logged):
    if logged.exercise.tracking != Exercise.Tracking.SETS:
        return redirect("training:session_log", logged.session_id)

    if request.method == "POST":
        form = SetForm(request.POST)
        if form.is_valid():
            services.add_set(logged, form.cleaned_data["weight_kg"], form.cleaned_data["reps"])
            return redirect("training:exercise_sets", logged.pk)
    else:
        last = logged.sets.order_by("-number").first()
        form = SetForm(initial={"weight_kg": last.weight_display, "reps": last.reps} if last else None)

    next_exercise = logged.session.exercises.filter(order__gt=logged.order).select_related("exercise").first()
    context = {"logged": logged, "sets": logged.sets.all(), "form": form, "next_exercise": next_exercise}
    return render(request, "training/exercise_sets.html", context)


@require_POST
@with_open_exercise
def set_delete_last(request, logged):
    services.delete_last_set(logged)
    return redirect("training:exercise_sets", logged.pk)


@require_POST
@with_open_exercise
def exercise_tick(request, logged):
    if logged.exercise.tracking != Exercise.Tracking.CHECK:
        raise Http404
    services.mark_done(logged, done=not logged.is_done)
    return redirect("training:session_log", logged.session_id)


@require_POST
@with_open_exercise
def exercise_move(request, logged, direction):
    if direction not in ("up", "down"):
        raise Http404
    services.move_exercise(logged, -1 if direction == "up" else 1)
    return redirect("training:session_log", logged.session_id)
