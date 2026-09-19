"""Creates the admin account and the starter triggers + templates.

Safe to run on every deploy: it never overwrites templates an admin edited.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from notifications.models import Channel, Template, Trigger

TRIGGERS = [
    {
        "key": "login", "name": "Login", "description": "User signs in on the website", "position": 10,
        "whatsapp": {"wa_name": "sb_login_alert", "title": "New sign-in",
                     "body": "Hi {{first_name}}, you just signed in to {{site_name}} at {{time}}. If this wasn't you, reset your password right away.",
                     "footer": "Signalboard security"},
        "email": {"title": "You signed in to {{site_name}}",
                  "body": "Hi {{first_name}},\n\nWelcome back! You signed in on {{date}} at {{time}} using {{device}}.\n\nIf this wasn't you, reset your password straight away.",
                  "cta_label": "Open my dashboard", "url": "{{site_url}}/app"},
        "webpush": {"title": "Welcome back, {{first_name}}!", "body": "You're signed in to {{site_name}}.", "url": "{{site_url}}/app"},
    },
    {
        "key": "logout", "name": "Logout", "description": "User signs out", "position": 20,
        "whatsapp": {"wa_name": "sb_logout_notice", "title": "",
                     "body": "Hi {{first_name}}, you signed out of {{site_name}} at {{time}}. See you again soon.", "footer": ""},
        "email": {"title": "You signed out of {{site_name}}",
                  "body": "Hi {{first_name}},\n\nYou signed out on {{date}} at {{time}}. Your account is safe.\n\nCome back any time.",
                  "cta_label": "Sign in again", "url": "{{site_url}}/login"},
        "webpush": {"title": "Signed out", "body": "See you soon, {{first_name}}. Your session is closed.", "url": "{{site_url}}"},
    },
    {
        "key": "inactive_1d", "name": "Not logged in for 1 day", "kind": "inactivity", "inactivity_days": 1,
        "description": "User hasn't visited for 24 hours", "position": 30,
        "whatsapp": {"wa_name": "sb_inactive_1d", "title": "",
                     "body": "Hi {{first_name}}, we haven't seen you on {{site_name}} since yesterday. Your dashboard is waiting.", "footer": ""},
        "email": {"title": "Your {{site_name}} dashboard is waiting",
                  "body": "Hi {{first_name}},\n\nIt's been a day since your last visit. Pick up right where you left off.",
                  "cta_label": "Continue", "url": "{{site_url}}/app"},
        "webpush": {"title": "Pick up where you left off", "body": "It's been a day, {{first_name}}. Come take a look.", "url": "{{site_url}}/app"},
    },
    {
        "key": "inactive_1w", "name": "Not logged in for 1 week", "kind": "inactivity", "inactivity_days": 7,
        "description": "User hasn't visited for 7 days", "position": 40,
        "whatsapp": {"wa_name": "sb_inactive_1w", "title": "We miss you",
                     "body": "Hi {{first_name}}, it's been {{days_inactive}} days since your last visit to {{site_name}}. Come back and see what's new.", "footer": ""},
        "email": {"title": "It's been a week, {{first_name}}",
                  "body": "Hi {{first_name}},\n\nWe miss you! It's been {{days_inactive}} days since your last visit.\n\nCome back and see what's new.",
                  "cta_label": "Come back", "url": "{{site_url}}/login"},
        "webpush": {"title": "We miss you!", "body": "Come visit {{site_name}} again, {{first_name}}.", "url": "{{site_url}}/login"},
    },
    {
        "key": "password_reset", "name": "Password reset", "description": "User asks to reset their password", "position": 50,
        "whatsapp": {"wa_name": "sb_password_reset", "title": "",
                     "body": "Hi {{first_name}}, we got a request to reset your {{site_name}} password. Check your email for the link.", "footer": ""},
        "email": {"title": "Reset your {{site_name}} password",
                  "body": "Hi {{first_name}},\n\nSomeone asked to reset the password for {{email}}. Use the button below to choose a new one.\n\nIf it wasn't you, ignore this email.",
                  "cta_label": "Reset password", "url": "{{reset_link}}"},
        "webpush": {"title": "Password reset requested", "body": "Check your inbox for the reset link.", "url": "{{site_url}}/login"},
    },
    {
        "key": "order_placed", "name": "Order placed", "description": "User completes a purchase", "position": 60,
        "whatsapp": {"wa_name": "sb_order_placed", "title": "Order confirmed",
                     "body": "Thanks {{first_name}}! Order {{order_id}} for {{order_total}} is confirmed. We'll message you when it ships.", "footer": ""},
        "email": {"title": "Order {{order_id}} confirmed",
                  "body": "Hi {{first_name}},\n\nThanks for your order! Order {{order_id}} for {{order_total}} is confirmed.\n\nWe'll let you know when it ships.",
                  "cta_label": "View order", "url": "{{site_url}}/app"},
        "webpush": {"title": "Order {{order_id}} confirmed", "body": "Thanks {{first_name}}! {{order_total}} paid.", "url": "{{site_url}}/app"},
    },
]


class Command(BaseCommand):
    help = "Create the admin user and starter triggers/templates (idempotent)."

    def handle(self, *args, **opts):
        self._admin()
        for spec in TRIGGERS:
            spec = dict(spec)
            channels = {c: spec.pop(c) for c in Channel.values}
            trigger, created = Trigger.objects.get_or_create(key=spec["key"], defaults=spec)
            if not created:
                continue
            for channel, fields in channels.items():
                Template.objects.create(
                    trigger=trigger, channel=channel,
                    # WhatsApp starts OFF until Meta approves it; email + push work immediately.
                    enabled=channel != Channel.WHATSAPP, **fields,
                )
            self.stdout.write(f"created trigger {trigger.key}")
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _admin(self):
        email = os.getenv("ADMIN_EMAIL", "admin@signalboard.dev").lower()
        password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=email, defaults={"email": email, "first_name": "Admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(password)
            user.save()
            user.profile.phone = "".join(ch for ch in os.getenv("ADMIN_PHONE", "") if ch.isdigit())
            user.profile.save()
            self.stdout.write(f"created admin {email}")
