from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path
from django.views.generic import TemplateView

from accounts.views import LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Legal pages, readable without logging in; linked from the login page.
    path("legal/", login_not_required(TemplateView.as_view(template_name="legal/notice.html")), name="legal_notice"),
    path("privacy/", login_not_required(TemplateView.as_view(template_name="legal/privacy.html")), name="privacy"),
    # Every page that has to do with training.
    path("", include("training.urls")),
]
