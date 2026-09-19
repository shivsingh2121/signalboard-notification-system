from django.conf import settings
from django.db import models


class Channel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    WEBPUSH = "webpush", "Web Push"


class Trigger(models.Model):
    """Something that happens on the website and should notify the user.

    kind=event       -> fired by website code (login, logout, order placed...)
    kind=inactivity  -> fired by the scheduler when a user hasn't been seen
                        for `inactivity_days`.
    """

    class Kind(models.TextChoices):
        EVENT = "event", "Website event"
        INACTIVITY = "inactivity", "Inactivity"

    key = models.SlugField(max_length=60, unique=True, help_text="Used by website code, e.g. 'login'")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EVENT)
    inactivity_days = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.name


class Template(models.Model):
    """One cell of the admin table: a trigger x channel message."""

    class WAStatus(models.TextChoices):
        DRAFT = "DRAFT", "Not submitted"
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAUSED = "PAUSED", "Paused"
        DISABLED = "DISABLED", "Disabled by Meta"
        ERROR = "ERROR", "Submit failed"

    class WACategory(models.TextChoices):
        UTILITY = "UTILITY", "Utility"
        MARKETING = "MARKETING", "Marketing"
        AUTHENTICATION = "AUTHENTICATION", "Authentication"

    trigger = models.ForeignKey(Trigger, on_delete=models.CASCADE, related_name="templates")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    enabled = models.BooleanField(default=True)

    # Email subject / push title / optional WhatsApp header
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, help_text="Use {{variables}} like {{name}}, {{site_name}}")
    # Email only: optional button
    cta_label = models.CharField(max_length=60, blank=True)
    # Email button link / push click-through URL
    url = models.CharField(max_length=500, blank=True)
    # WhatsApp only
    footer = models.CharField(max_length=60, blank=True)

    # Web push platforms (Web Push only — iOS/Android always off for this project)
    push_ios = models.BooleanField(default=False)
    push_android = models.BooleanField(default=False)

    # WhatsApp Cloud API template metadata
    wa_name = models.CharField(max_length=512, blank=True)
    wa_language = models.CharField(max_length=15, default="en_US")
    wa_category = models.CharField(max_length=20, choices=WACategory.choices, default=WACategory.UTILITY)
    wa_use_existing = models.BooleanField(default=False, help_text="Link a template that already exists in Meta")
    wa_template_id = models.CharField(max_length=64, blank=True)
    wa_status = models.CharField(max_length=20, choices=WAStatus.choices, default=WAStatus.DRAFT)
    wa_status_reason = models.CharField(max_length=500, blank=True)
    # Ordered list of variable names mapped to {{1}}, {{2}}... in the Meta template
    variable_mapping = models.JSONField(default=list, blank=True)
    wa_synced_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("trigger", "channel")
        ordering = ["trigger__position", "channel"]

    def __str__(self):
        return f"{self.trigger.key}/{self.channel}"

    @property
    def is_sendable(self):
        if self.channel == Channel.WHATSAPP:
            return self.wa_status == self.WAStatus.APPROVED
        return True


class TriggerEvent(models.Model):
    """Every time a trigger fires (used for the activity feed and inactivity de-dupe)."""

    trigger = models.ForeignKey(Trigger, on_delete=models.CASCADE, related_name="events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trigger_events", null=True)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class NotificationLog(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    event = models.ForeignKey(TriggerEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    trigger = models.ForeignKey(Trigger, on_delete=models.SET_NULL, null=True, related_name="logs")
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    recipient = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    is_test = models.BooleanField(default=False)
    rendered_title = models.CharField(max_length=255, blank=True)
    rendered_body = models.TextField(blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
