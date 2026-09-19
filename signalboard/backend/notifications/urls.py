from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("admin/triggers", views.TriggerViewSet, basename="trigger")
router.register("admin/templates", views.TemplateViewSet, basename="template")
router.register("admin/logs", views.LogViewSet, basename="log")
router.register("admin/users", views.AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("health/", views.health),
    path("variables/", views.variables),
    path("events/order/", views.place_order),
    path("me/notifications/", views.my_notifications),
    path("cron/inactivity/", views.cron_inactivity),
    path("admin/overview/", views.overview),
    path("admin/events/", views.recent_events),
    path("admin/run-inactivity-check/", views.admin_run_inactivity),
    path("", include(router.urls)),
]
