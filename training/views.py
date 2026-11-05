from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from .models import Session
from .services import get_open_session


def history(request):
    open_session = get_open_session(request.user)
    sessions = (
        Session.objects.filter(athlete=request.user, finished_at__isnull=False)
        .annotate(exercise_count=Count("exercises", distinct=True), set_count=Count("exercises__sets", distinct=True))
        .prefetch_related("exercises__exercise__category")
    )
    return render(request, "training/history.html", {"sessions": sessions, "open_session": open_session})


def session_detail(request, pk):
    session = get_object_or_404(Session, pk=pk, athlete=request.user)
    exercises = session.exercises.select_related("exercise__category").prefetch_related("sets")
    return render(request, "training/session_detail.html", {"session": session, "exercises": exercises})
