"""Fires triggers and delivers each enabled channel template."""
import logging
import threading

from django.conf import settings
from django.db import close_old_connections

from .models import Channel, NotificationLog, Template, Trigger, TriggerEvent
from .renderer import build_context, render
from .services import NotConfigured, ProviderError
from .services import email as email_service
from .services import webpush as push_service
from .services import whatsapp as wa_service

log = logging.getLogger(__name__)


def recipient_for(channel, user):
    if channel == Channel.WHATSAPP:
        return getattr(getattr(user, "profile", None), "phone", "")
    if channel == Channel.EMAIL:
        return user.email
    return getattr(getattr(user, "profile", None), "push_subscription_id", "") or f"user:{user.pk}"


def deliver(template, user, ctx, *, to=None, is_test=False, event=None):
    """Send one template to one user. Always returns a NotificationLog."""
    channel = template.channel
    title = render(template.title, ctx)
    body = render(template.body, ctx)
    url = render(template.url, ctx)
    recipient = (to or recipient_for(channel, user) or "").strip()

    entry = NotificationLog(
        event=event, trigger=template.trigger, template=template, channel=channel, user=user,
        recipient=recipient, is_test=is_test, rendered_title=title[:255], rendered_body=body,
    )
    try:
        if not recipient:
            raise NotConfigured("This user has no WhatsApp number on their profile.")
        if channel == Channel.WHATSAPP:
            recipient = "".join(ch for ch in recipient if ch.isdigit())
            entry.recipient = recipient
            entry.provider_message_id = wa_service.send(template, recipient, ctx)
        elif channel == Channel.EMAIL:
            html_body = email_service.build_html(title, body, template.cta_label, url)
            entry.provider_message_id = email_service.send(recipient, title, body, html_body)
        elif channel == Channel.WEBPUSH:
            entry.provider_message_id = push_service.send(user, title, body, url)
        entry.status = NotificationLog.Status.SENT
    except NotConfigured as exc:
        entry.status = NotificationLog.Status.SKIPPED
        entry.error = str(exc)
    except ProviderError as exc:
        entry.status = NotificationLog.Status.FAILED
        entry.error = str(exc)
    except Exception as exc:  # never let one channel break the others
        log.exception("Unexpected error delivering %s", template)
        entry.status = NotificationLog.Status.FAILED
        entry.error = f"Unexpected error: {exc}"
    entry.save()
    return entry


def _dispatch(event_id):
    try:
        event = TriggerEvent.objects.select_related("trigger", "user__profile").get(pk=event_id)
        ctx = build_context(event.user, event.context)
        templates = Template.objects.filter(trigger=event.trigger, enabled=True)
        return [deliver(t, event.user, ctx, event=event) for t in templates]
    finally:
        if settings.NOTIFY_ASYNC:
            close_old_connections()


def fire_trigger(key, user, context=None, run_async=None):
    """Call this from website code whenever something happens.

    Returns the TriggerEvent (or None if the trigger doesn't exist / is paused).
    """
    trigger = Trigger.objects.filter(key=key, is_active=True).first()
    if not trigger or user is None:
        return None
    event = TriggerEvent.objects.create(trigger=trigger, user=user, context=context or {})
    run_async = settings.NOTIFY_ASYNC if run_async is None else run_async
    if run_async:
        threading.Thread(target=_dispatch, args=(event.pk,), daemon=True).start()
    else:
        _dispatch(event.pk)
    return event
