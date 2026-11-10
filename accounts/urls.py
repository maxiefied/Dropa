from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import PhoneLoginForm

app_name = "accounts"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            authentication_form=PhoneLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
