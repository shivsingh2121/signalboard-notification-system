from datetime import timedelta
import secrets
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .dispatcher import deliver, fire_trigger
from .inactivity import run_inactivity_check
from .models import Channel, NotificationLog, Template, Trigger, TriggerEvent
from .renderer import VARIABLES, build_context
from .serializers import AdminUserSerializer, LogSerializer, TemplateSerializer, TriggerSerializer
from .services import NotConfigured, ProviderError
from .services import email as email_service
from .services import webpush as push_service
from .services import whatsapp as wa_service

User = get_user_model()


# ---------- public / user-facing ----------

@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    return Response({"status": "ok", "time": timezone.now()})


@api_view(["GET"])
@permission_classes([AllowAny])
def variables(_request):
    return Response([{"name": k, "description": d, "sample": s} for k, (d, s) in VARIABLES.items()])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def place_order(request):
    """Demo website action that fires the 'order_placed' trigger."""
    order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    total = request.data.get("total") or "₹1,499"
    event = fire_trigger("order_placed", request.user, {"order_id": order_id, "order_total": total})
    return Response({"order_id": order_id, "order_total": total, "notified": bool(event)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    logs = NotificationLog.objects.filter(user=request.user, is_test=False).select_related("trigger")[:30]
    return Response(LogSerializer(logs, many=True).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def cron_inactivity(request):
    """For a Render Cron Job / uptime pinger: POST with header X-Cron-Secret."""
    given = request.headers.get("X-Cron-Secret", "")
    if not settings.CRON_SECRET or not secrets.compare_digest(given, settings.CRON_SECRET):
        return Response({"detail": "Invalid cron secret."}, status=status.HTTP_403_FORBIDDEN)
    return Response({"fired": run_inactivity_check()})


# ---------- admin ----------

def provider_status():
    return {
        "whatsapp": {
            "configured": wa_service.is_configured(),
            "templates_configured": wa_service.templates_configured(),
            "provider": "WhatsApp Cloud API",
            "api_version": settings.WHATSAPP_API_VERSION,
        },
        "email": {
            "configured": email_service.is_configured(),
            "provider": email_service.provider(),
            "from": email_service.from_email(),
        },
        "webpush": {
            "configured": push_service.is_configured(),
            "provider": "OneSignal",
            "app_id": settings.ONESIGNAL_APP_ID,
        },
    }


@api_view(["GET"])
@permission_classes([IsAdminUser])
def overview(_request):
    since = timezone.now() - timedelta(days=7)
    recent = NotificationLog.objects.filter(created_at__gte=since)
    return Response({
        "providers": provider_status(),
        "stats": {
            "triggers": Trigger.objects.count(),
            "active_templates": Template.objects.filter(enabled=True).count(),
            "users": User.objects.count(),
            "sent_7d": recent.filter(status="sent").count(),
            "failed_7d": recent.filter(status="failed").count(),
        },
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_run_inactivity(_request):
    return Response({"fired": run_inactivity_check()})


class TriggerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = TriggerSerializer

    def get_queryset(self):
        return TriggerSerializer.annotated(Trigger.objects.all())

    def perform_create(self, serializer):
        last = Trigger.objects.order_by("-position").first()
        serializer.save(position=(last.position + 10) if last else 10)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        self.perform_create(s)
        obj = self.get_queryset().get(pk=s.instance.pk)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(self.get_serializer(self.get_queryset().get(pk=kwargs["pk"])).data)

    def perform_destroy(self, instance):
        for t in instance.templates.filter(channel=Channel.WHATSAPP):
            wa_service.delete_remote(t)
        instance.delete()


WA_CONTENT_FIELDS = {"title", "body", "footer", "wa_name", "wa_language", "wa_category", "wa_use_existing"}


class TemplateViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin,
                      mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = TemplateSerializer
    queryset = Template.objects.select_related("trigger")

    def _after_save(self, template, changed_fields):
        """WhatsApp templates are submitted to Meta straight from the admin panel."""
        from .renderer import find_variables

        notice = None
        if template.channel != Channel.WHATSAPP:
            return notice
        if template.wa_use_existing:
            template.variable_mapping = find_variables(template.body)
            template.save(update_fields=["variable_mapping"])
        if not (changed_fields & WA_CONTENT_FIELDS):
            return notice
        try:
            wa_service.submit(template)
            notice = ("Linked to the existing Meta template." if template.wa_use_existing
                      else "Submitted to Meta for review. Press Sync to check approval.")
        except ProviderError as exc:
            if not template.wa_template_id:
                template.wa_status = Template.WAStatus.ERROR
            template.wa_status_reason = str(exc)[:500]
            template.save(update_fields=["wa_status", "wa_status_reason"])
            notice = f"Saved, but Meta didn't accept it yet: {exc}"
        return notice

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        if Template.objects.filter(trigger=s.validated_data["trigger"], channel=s.validated_data["channel"]).exists():
            return Response({"detail": "This trigger already has a template for that channel."}, status=400)
        template = s.save()
        notice = self._after_save(template, WA_CONTENT_FIELDS)
        template.refresh_from_db()
        return Response({**TemplateSerializer(template).data, "notice": notice}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        template = self.get_object()
        before = {f: getattr(template, f) for f in WA_CONTENT_FIELDS}
        s = self.get_serializer(template, data=request.data, partial=kwargs.pop("partial", False))
        s.is_valid(raise_exception=True)
        # Renaming or relinking means a different Meta template: start fresh.
        if template.channel == Channel.WHATSAPP and (
            s.validated_data.get("wa_name", template.wa_name) != template.wa_name
            or s.validated_data.get("wa_language", template.wa_language) != template.wa_language
            or s.validated_data.get("wa_use_existing", template.wa_use_existing) != template.wa_use_existing
        ):
            template.wa_template_id = ""
            template.wa_status = Template.WAStatus.DRAFT
        template = s.save()
        changed = {f for f in WA_CONTENT_FIELDS if getattr(template, f) != before[f]}
        if template.channel == Channel.WHATSAPP and template.wa_status in (Template.WAStatus.DRAFT, Template.WAStatus.ERROR):
            changed |= {"body"}  # never submitted successfully — try again
        notice = self._after_save(template, changed)
        template.refresh_from_db()
        return Response({**TemplateSerializer(template).data, "notice": notice})

    def perform_destroy(self, instance):
        if instance.channel == Channel.WHATSAPP:
            wa_service.delete_remote(instance)
        instance.delete()

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        template = self.get_object()
        enabled = request.data.get("enabled")
        template.enabled = (not template.enabled) if enabled is None else bool(enabled)
        template.save(update_fields=["enabled", "updated_at"])
        return Response(TemplateSerializer(template).data)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        template = self.get_object()
        if template.channel != Channel.WHATSAPP:
            return Response({"detail": "Only WhatsApp templates need syncing."}, status=400)
        try:
            wa_service.sync(template)
        except ProviderError as exc:
            return Response({"detail": str(exc)}, status=502)
        return Response(TemplateSerializer(template).data)

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        """Send this template to the admin (or a given phone/email) right now, even if toggled off."""
        template = self.get_object()
        user = request.user
        to = (request.data.get("to") or "").strip() or None
        if template.channel == Channel.WEBPUSH and request.data.get("user_id"):
            user = User.objects.filter(pk=request.data["user_id"]).first() or user
            to = None
        ctx = build_context(user, {
            "device": request.META.get("HTTP_USER_AGENT", ""),
            "order_id": "ORD-TEST1", "order_total": "₹1,499", "days_inactive": "7",
            "reset_link": f"{settings.FRONTEND_URL}/login?reset=demo",
        })
        entry = deliver(template, user, ctx, to=to, is_test=True)
        code = 200 if entry.status == NotificationLog.Status.SENT else 422
        return Response(LogSerializer(entry).data, status=code)


class LogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = LogSerializer

    def get_queryset(self):
        qs = NotificationLog.objects.select_related("trigger", "user")
        p = self.request.query_params
        if p.get("channel"):
            qs = qs.filter(channel=p["channel"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("trigger"):
            qs = qs.filter(trigger_id=p["trigger"])
        if p.get("q"):
            qs = qs.filter(Q(recipient__icontains=p["q"]) | Q(user__email__icontains=p["q"]))
        return qs[:200]


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.select_related("profile").order_by("-date_joined")

    @action(detail=True, methods=["post"], url_path="simulate-inactive")
    def simulate_inactive(self, request, pk=None):
        """Demo helper: pretend this user was last seen N days ago."""
        user = self.get_object()
        try:
            days = max(1, min(365, int(request.data.get("days", 8))))
        except (TypeError, ValueError):
            return Response({"detail": "days must be a number."}, status=400)
        user.profile.last_seen = timezone.now() - timedelta(days=days, minutes=1)
        user.profile.save(update_fields=["last_seen"])
        return Response(AdminUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def fire(self, request, pk=None):
        """Demo helper: fire any trigger for this user as if it happened on the site."""
        user = self.get_object()
        trigger = Trigger.objects.filter(pk=request.data.get("trigger")).first()
        if not trigger:
            return Response({"detail": "Pick a trigger."}, status=400)
        if not trigger.is_active:
            return Response({"detail": f"'{trigger.name}' is paused. Turn it on first."}, status=400)
        event = fire_trigger(trigger.key, user, {
            "order_id": "ORD-DEMO1", "order_total": "₹1,499",
            "days_inactive": str(trigger.inactivity_days or ""),
            "reset_link": f"{settings.FRONTEND_URL}/login?reset=demo",
        }, run_async=False)
        logs = NotificationLog.objects.filter(event=event)
        return Response({"event": event.pk, "results": LogSerializer(logs, many=True).data})


@api_view(["GET"])
@permission_classes([IsAdminUser])
def recent_events(_request):
    events = TriggerEvent.objects.select_related("trigger", "user").prefetch_related("logs")[:40]
    return Response([{
        "id": e.id, "trigger": e.trigger.name, "user": e.user.email if e.user else "",
        "created_at": e.created_at,
        "channels": {log.channel: log.status for log in e.logs.all()},
    } for e in events])
