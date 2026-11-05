from django.urls import path

from . import views

app_name = "training"

urlpatterns = [
    path("", views.history, name="history"),
    path("sessions/<uuid:pk>/", views.session_detail, name="session_detail"),
]
