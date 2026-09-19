"""Check that WhatsApp, Email and Web Push keys actually work.

    python manage.py verify_channels
    python manage.py verify_channels --phone 919876543210 --email you@example.com

Without flags it only makes read-only calls (nothing is sent).
With --phone / --email it sends one real test message on that channel.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.services import ProviderError
from notifications.services import email as email_service
from notifications.services import webpush as push_service
from notifications.services import whatsapp as wa_service

TIMEOUT = 15


class Command(BaseCommand):
    help = "Check provider keys (read-only), optionally send real test messages."

    def add_arguments(self, parser):
        parser.add_argument("--phone", help="Send WhatsApp 'hello_world' to this number (country code, digits)")
        parser.add_argument("--email", help="Send a real test email to this address")

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f"  ✔ {msg}"))

    def bad(self, msg):
        self.stdout.write(self.style.ERROR(f"  ✘ {msg}"))
        self.failed = True

    def handle(self, *args, **opts):
        self.failed = False
        self.check_database()
        self.check_whatsapp(opts.get("phone"))
        self.check_email(opts.get("email"))
        self.check_webpush()
        self.stdout.write("")
        if self.failed:
            self.stdout.write(self.style.ERROR("Some checks failed — fix the ✘ lines above."))
        else:
            self.stdout.write(self.style.SUCCESS("All checks passed."))

    # ---------------------------------------------------------------
    def check_database(self):
        from django.db import connection

        self.stdout.write("\nDatabase")
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            self.ok(f"Connected ({connection.vendor}, {connection.settings_dict.get('HOST') or 'local file'})")
        except Exception as exc:  # noqa: BLE001
            self.bad(f"Cannot connect: {exc}")

    def check_whatsapp(self, phone):
        self.stdout.write("\nWhatsApp Cloud API")
        if not wa_service.is_configured():
            return self.bad("WHATSAPP_ACCESS_TOKEN or PHONE_NUMBER_ID missing")
        base = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

        # 1. Token + phone number id
        try:
            r = requests.get(f"{base}/{settings.WHATSAPP_PHONE_NUMBER_ID}", headers=headers, timeout=TIMEOUT,
                             params={"fields": "display_phone_number,verified_name"})
            data = r.json()
            if r.status_code >= 400:
                return self.bad(f"Token/phone id rejected: {data.get('error', {}).get('message', data)}")
            self.ok(f"Token works — sending from {data.get('display_phone_number')} ({data.get('verified_name')})")
        except requests.RequestException as exc:
            return self.bad(f"Could not reach Meta: {exc}")

        # 2. Token expiry
        try:
            r = requests.get(f"{base}/debug_token", headers=headers, timeout=TIMEOUT,
                             params={"input_token": settings.WHATSAPP_ACCESS_TOKEN})
            info = r.json().get("data", {})
            expires = info.get("expires_at")
            if expires == 0:
                self.ok("Token never expires (System User token) ✅")
            elif expires:
                from datetime import datetime
                when = datetime.fromtimestamp(expires).strftime("%d %b %Y %H:%M")
                self.stdout.write(self.style.WARNING(
                    f"  ! Temporary token — expires {when}. Create a System User token with expiry 'Never'."))
        except (requests.RequestException, ValueError):
            self.stdout.write("  ? Could not read token expiry (not critical)")

        # 3. Template management
        if not wa_service.templates_configured():
            self.bad("WHATSAPP_BUSINESS_ACCOUNT_ID missing — admin panel can't create/sync templates")
        else:
            r = requests.get(f"{base}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates", headers=headers,
                             timeout=TIMEOUT, params={"limit": 50, "fields": "name,status"})
            if r.status_code >= 400:
                self.bad(f"WABA id / template permission problem: {r.json().get('error', {}).get('message')}")
            else:
                tpls = r.json().get("data", [])
                approved = [t["name"] for t in tpls if t.get("status") == "APPROVED"]
                self.ok(f"Can read templates — {len(tpls)} found, approved: {', '.join(approved) or 'none yet'}")

        # 4. Optional real send
        if phone:
            to = "".join(ch for ch in phone if ch.isdigit())
            r = requests.post(f"{base}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages", headers=headers, timeout=TIMEOUT, json={
                "messaging_product": "whatsapp", "to": to, "type": "template",
                "template": {"name": "hello_world", "language": {"code": "en_US"}},
            })
            if r.status_code >= 400:
                self.bad(f"Send to {to} failed: {r.json().get('error', {}).get('message')} "
                         "(is this number added as a test recipient in Meta?)")
            else:
                self.ok(f"hello_world sent to {to} — check the phone")

    def check_email(self, to):
        p = email_service.provider()
        self.stdout.write(f"\nEmail ({p})")
        if p == "console":
            return self.stdout.write(self.style.WARNING("  ! EMAIL_PROVIDER=console — emails only print in the terminal"))
        if not email_service.is_configured():
            return self.bad("API key or verified sender email missing")
        checks = {
            "postmark": ("https://api.postmarkapp.com/server", {"X-Postmark-Server-Token": settings.POSTMARK_TOKEN, "Accept": "application/json"}),
            "brevo": ("https://api.brevo.com/v3/account", {"api-key": settings.BREVO_API_KEY, "accept": "application/json"}),
            "resend": ("https://api.resend.com/domains", {"Authorization": f"Bearer {settings.RESEND_API_KEY}"}),
        }
        url, headers = checks[p]
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
            if r.status_code >= 400:
                return self.bad(f"Key rejected ({r.status_code}): {r.text[:150]}")
            self.ok(f"API key works — sender {email_service.from_email()}")
        except requests.RequestException as exc:
            return self.bad(f"Could not reach {p}: {exc}")
        if to:
            try:
                html = email_service.build_html("Signalboard test", "If you can read this, email delivery works.")
                mid = email_service.send(to, "Signalboard test", "If you can read this, email delivery works.", html)
                self.ok(f"Test email sent to {to} (id {mid}) — check inbox and spam")
            except ProviderError as exc:
                self.bad(str(exc))

    def check_webpush(self):
        self.stdout.write("\nWeb Push (OneSignal)")
        if not push_service.is_configured():
            return self.bad("ONESIGNAL_APP_ID or ONESIGNAL_REST_API_KEY missing")
        # Sending to a non-existent subscription tells us whether the key is valid without notifying anyone.
        r = requests.post(push_service.URL, timeout=TIMEOUT, headers={
            "Authorization": push_service._auth_header(), "Content-Type": "application/json"}, json={
            "app_id": settings.ONESIGNAL_APP_ID, "target_channel": "push",
            "include_subscription_ids": ["00000000-0000-0000-0000-000000000000"],
            "contents": {"en": "key check"},
        })
        if r.status_code in (401, 403):
            return self.bad("REST API key rejected — copy it again from OneSignal > Settings > Keys & IDs")
        if r.status_code == 400 and "app_id" in r.text.lower():
            return self.bad(f"App ID problem: {r.text[:150]}")
        self.ok("App ID + REST API key accepted (subscribe in the browser, then use Test in the admin panel)")
