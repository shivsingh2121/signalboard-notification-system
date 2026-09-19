from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root(_request):
    return JsonResponse({"service": "signalboard-api", "status": "ok", "docs": "/api/health/"})


urlpatterns = [
    path("", root),
    path("django-admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("notifications.urls")),
]
