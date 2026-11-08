from django.contrib.auth import views as auth_views
from django.shortcuts import redirect


class LogoutView(auth_views.LogoutView):
    """Logging out needs the button (a POST), so other websites cannot log
    anyone out. Opening /logout/ directly just goes back to the app."""

    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        return redirect("training:history")
