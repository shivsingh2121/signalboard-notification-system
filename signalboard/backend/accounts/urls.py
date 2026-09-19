from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.register),
    path("login/", views.login),
    path("logout/", views.logout),
    path("me/", views.me),
    path("push-subscription/", views.push_subscription),
    path("password-reset/", views.password_reset),
]
