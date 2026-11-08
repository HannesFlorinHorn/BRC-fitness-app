from django.urls import path

from . import views

app_name = "training"

urlpatterns = [
    #View History GET
    path("", views.history, name="history"),
    # view to start new session GET
    path("sessions/new/", views.start, name="start"),
    # view to look into a logged session GET
    path("sessions/<uuid:pk>/", views.session_detail, name="session_detail"),
    # overview in open log GET
    path("sessions/<uuid:pk>/log/", views.session_log, name="session_log"),
    
    # search to add a new exercise GET (Choose one -> POST -> Redirect -> GET )
    path("sessions/<uuid:pk>/add-exercise/", views.exercise_add, name="exercise_add"),
    
    # end the session POST
    path("sessions/<uuid:pk>/finish/", views.session_finish, name="session_finish"),
    # logging an exercice with its Sets  GET/POST 
    path("logged/<uuid:pk>/", views.exercise_sets, name="exercise_sets"),
    # delete last Set POST 
    path("logged/<uuid:pk>/delete-last-set/", views.set_delete_last, name="set_delete_last"),
    # tick a exercice done POST
    path("logged/<uuid:pk>/tick/", views.exercise_tick, name="exercise_tick"),
    # move an exercice 
    path("logged/<uuid:pk>/move/<str:direction>/", views.exercise_move, name="exercise_move"),
]
