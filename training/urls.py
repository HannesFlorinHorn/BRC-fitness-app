from django.urls import path

from . import views

app_name = "training"

urlpatterns = [
    path("", views.history, name="history"),
    path("sessions/new/", views.start, name="start"),
    path("sessions/<uuid:pk>/", views.session_detail, name="session_detail"),
    path("sessions/<uuid:pk>/log/", views.session_log, name="session_log"),
    path("sessions/<uuid:pk>/add-exercise/", views.exercise_add, name="exercise_add"),
    path("sessions/<uuid:pk>/finish/", views.session_finish, name="session_finish"),
    path("logged/<uuid:pk>/", views.exercise_sets, name="exercise_sets"),
    path("logged/<uuid:pk>/delete-last-set/", views.set_delete_last, name="set_delete_last"),
    path("logged/<uuid:pk>/tick/", views.exercise_tick, name="exercise_tick"),
    path("logged/<uuid:pk>/move/<str:direction>/", views.exercise_move, name="exercise_move"),
]
