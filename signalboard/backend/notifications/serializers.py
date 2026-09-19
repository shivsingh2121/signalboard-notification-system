import re

from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from rest_framework import serializers

from .models import Channel, NotificationLog, Template, Trigger
from .renderer import VAR_RE, VARIABLES, find_variables, render, sample_context

User = get_user_model()
WA_NAME_RE = re.compile(r"^[a-z0-9_]{1,512}$")


class TemplateSerializer(serializers.ModelSerializer):
    variables = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    wa_status_label = serializers.CharField(source="get_wa_status_display", read_only=True)
    is_sendable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Template
        fields = [
            "id", "trigger", "channel", "enabled", "title", "body", "cta_label", "url", "footer",
            "push_ios", "push_android",
            "wa_name", "wa_language", "wa_category", "wa_use_existing", "wa_template_id",
            "wa_status", "wa_status_label", "wa_status_reason", "wa_synced_at", "variable_mapping",
            "variables", "preview", "is_sendable", "updated_at",
        ]
        read_only_fields = ["wa_template_id", "wa_status", "wa_status_reason", "wa_synced_at", "variable_mapping"]

    def get_variables(self, obj):
        return find_variables(f"{obj.title} {obj.body} {obj.url}")

    def get_preview(self, obj):
        ctx = sample_context()
        return {"title": render(obj.title, ctx), "body": render(obj.body, ctx), "url": render(obj.url, ctx)}

    def validate(self, attrs):
        inst = self.instance
        get = lambda f: attrs.get(f, getattr(inst, f, None) if inst else None)  # noqa: E731
        channel = get("channel")
        if inst and "channel" in attrs and attrs["channel"] != inst.channel:
            raise serializers.ValidationError({"channel": "A template's channel can't be changed."})
        if inst and "trigger" in attrs and attrs["trigger"] != inst.trigger:
            raise serializers.ValidationError({"trigger": "A template's trigger can't be changed."})

        body = (get("body") or "").strip()
        title = (get("title") or "").strip()
        errors = {}

        unknown = [v for v in find_variables(f"{title} {body} {get('url') or ''}") if v not in VARIABLES]
        if unknown:
            errors["body"] = f"Unknown variable(s): {', '.join(unknown)}. Pick from the variables list."

        if channel in (Channel.EMAIL, Channel.WEBPUSH) and not body:
            errors["body"] = "Write the message."
        if channel == Channel.EMAIL and not title:
            errors["title"] = "Email needs a subject line."
        if channel == Channel.WEBPUSH:
            if not title:
                errors["title"] = "Browser alerts need a title."
            if len(body) > 240:
                errors["body"] = "Keep browser alerts under 240 characters — browsers cut off longer text."
            if get("push_ios") or get("push_android"):
                errors["push_ios"] = "This project sends Web Push only. Keep iOS and Android off."
        if channel == Channel.WHATSAPP:
            name = (get("wa_name") or "").strip()
            if not WA_NAME_RE.match(name):
                errors["wa_name"] = "Use lowercase letters, numbers and underscores only, e.g. login_welcome."
            if not get("wa_use_existing"):
                if not body:
                    errors["body"] = "Write the message body."
                elif re.match(r"^\s*\{\{", body) or re.search(r"\}\}\s*[.!?]?\s*$", body):
                    errors["body"] = "Meta rejects templates that start or end with a variable. Add text before/after it."
                if len(body) > 1024:
                    errors["body"] = "WhatsApp body can be at most 1024 characters."
                if VAR_RE.search(title):
                    errors["title"] = "Keep the WhatsApp header plain text (no variables)."
                if len(title) > 60:
                    errors["title"] = "WhatsApp header can be at most 60 characters."
        if errors:
            raise serializers.ValidationError(errors)
        if "body" in attrs:
            attrs["body"] = body
        return attrs


class TriggerSerializer(serializers.ModelSerializer):
    templates = serializers.SerializerMethodField()
    fired_count = serializers.IntegerField(read_only=True, default=0)
    last_fired = serializers.DateTimeField(read_only=True, default=None)

    class Meta:
        model = Trigger
        fields = ["id", "key", "name", "description", "kind", "inactivity_days", "is_active", "position",
                  "templates", "fired_count", "last_fired", "created_at"]

    def get_templates(self, obj):
        by_channel = {t.channel: TemplateSerializer(t).data for t in obj.templates.all()}
        return {c: by_channel.get(c) for c in Channel.values}

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", Trigger.Kind.EVENT))
        days = attrs.get("inactivity_days", getattr(self.instance, "inactivity_days", None))
        if kind == Trigger.Kind.INACTIVITY and not days:
            raise serializers.ValidationError({"inactivity_days": "Say after how many days of no visits this fires."})
        if kind == Trigger.Kind.EVENT:
            attrs["inactivity_days"] = None
        return attrs

    @staticmethod
    def annotated(qs):
        return qs.annotate(fired_count=Count("events", distinct=True), last_fired=Max("events__created_at")) \
                 .prefetch_related("templates").order_by("position", "id")


class LogSerializer(serializers.ModelSerializer):
    trigger_name = serializers.CharField(source="trigger.name", default="", read_only=True)
    user_email = serializers.CharField(source="user.email", default="", read_only=True)

    class Meta:
        model = NotificationLog
        fields = ["id", "trigger_name", "channel", "user_email", "recipient", "status", "is_test",
                  "rendered_title", "rendered_body", "provider_message_id", "error", "created_at"]


class AdminUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    phone = serializers.CharField(source="profile.phone", default="")
    push_subscribed = serializers.SerializerMethodField()
    last_seen = serializers.DateTimeField(source="profile.last_seen", default=None)

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "push_subscribed", "last_seen", "is_staff", "date_joined"]

    def get_name(self, obj):
        return obj.get_full_name() or obj.email.split("@")[0]

    def get_push_subscribed(self, obj):
        return bool(getattr(obj, "profile", None) and obj.profile.push_subscription_id)
