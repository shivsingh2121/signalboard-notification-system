from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import NotificationLog, Template, Trigger
from .renderer import render, to_positional

User = get_user_model()


class FakeResp:
    def __init__(self, status, data):
        self.status_code, self._data, self.text = status, data, str(data)

    def json(self):
        return self._data


@override_settings(
    NOTIFY_ASYNC=False, EMAIL_PROVIDER="console",
    WHATSAPP_ACCESS_TOKEN="tok", WHATSAPP_PHONE_NUMBER_ID="111", WHATSAPP_BUSINESS_ACCOUNT_ID="222",
    ONESIGNAL_APP_ID="app", ONESIGNAL_REST_API_KEY="os_v2_app_key", CRON_SECRET="s3cret",
)
class FlowTests(TestCase):
    def setUp(self):
        call_command("seed_notifications", verbosity=0)
        self.client = APIClient()
        self.admin = User.objects.get(username="admin@signalboard.dev")
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

    def register(self, email="riya@example.com"):
        r = self.client.post("/api/auth/register/", {"name": "Riya Sharma", "email": email, "password": "secret123", "phone": "+91 98765 43210"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_renderer_and_positional(self):
        self.assertEqual(render("Hi {{ name }}!", {"name": "A"}), "Hi A!")
        body, mapping = to_positional("Hi {{name}}, {{site_name}} says hi {{name}}.")
        self.assertEqual(body, "Hi {{1}}, {{2}} says hi {{1}}.")
        self.assertEqual(mapping, ["name", "site_name"])

    @mock.patch("notifications.services.webpush.requests.post")
    def test_login_fires_email_and_push(self, post):
        post.return_value = FakeResp(200, {"id": "push-1"})
        self.register()
        r = self.client.post("/api/auth/login/", {"email": "RIYA@example.com", "password": "secret123"}, format="json")
        self.assertEqual(r.status_code, 200)
        logs = NotificationLog.objects.filter(trigger__key="login")
        self.assertEqual({l.channel: l.status for l in logs}, {"email": "sent", "webpush": "sent"})
        self.assertIn("Riya", logs.get(channel="email").rendered_body)
        # push falls back to external_id when no subscription id stored
        self.assertIn("include_aliases", post.call_args.kwargs["json"])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Key os_v2_app_key")

    @mock.patch("notifications.services.webpush.requests.post")
    def test_logout_fires_and_revokes_token(self, post):
        post.return_value = FakeResp(200, {"id": "push-2"})
        token = self.register()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.client.post("/api/auth/push-subscription/", {"subscription_id": "sub-123"}, format="json")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        self.assertEqual(post.call_args.kwargs["json"]["include_subscription_ids"], ["sub-123"])
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_toggle_off_skips_channel(self):
        email_tpl = Template.objects.get(trigger__key="login", channel="email")
        r = self.admin_client.post(f"/api/admin/templates/{email_tpl.pk}/toggle/")
        self.assertFalse(r.data["enabled"])
        self.register()
        with mock.patch("notifications.services.webpush.requests.post", return_value=FakeResp(200, {"id": "x"})):
            self.client.post("/api/auth/login/", {"email": "riya@example.com", "password": "secret123"}, format="json")
        self.assertFalse(NotificationLog.objects.filter(trigger__key="login", channel="email").exists())

    def test_matrix_shape(self):
        r = self.admin_client.get("/api/admin/triggers/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 6)
        self.assertEqual(set(r.data[0]["templates"].keys()), {"whatsapp", "email", "webpush"})

    def test_non_admin_blocked(self):
        token = self.register()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.get("/api/admin/triggers/").status_code, 403)

    @mock.patch("notifications.services.whatsapp.requests.request")
    def test_whatsapp_create_sync_and_send(self, req):
        trig = self.admin_client.post("/api/admin/triggers/", {"key": "welcome", "name": "Welcome"}, format="json").data
        req.return_value = FakeResp(200, {"id": "tpl-9", "status": "PENDING", "category": "UTILITY"})
        r = self.admin_client.post("/api/admin/templates/", {
            "trigger": trig["id"], "channel": "whatsapp", "wa_name": "welcome_msg",
            "body": "Hello {{first_name}}, welcome to {{site_name}} today.",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["wa_status"], "PENDING")
        self.assertEqual(r.data["variable_mapping"], ["first_name", "site_name"])
        sent_payload = req.call_args.kwargs["json"]
        self.assertEqual(sent_payload["components"][0]["text"], "Hello {{1}}, welcome to {{2}} today.")
        self.assertIn("example", sent_payload["components"][0])

        # test send before approval is refused with a clear reason
        r = self.admin_client.post(f"/api/admin/templates/{r.data['id']}/test/", {"to": "919999999999"}, format="json")
        self.assertEqual(r.status_code, 422)
        self.assertIn("Sync", r.data["error"])

        tpl_id = r.data and Template.objects.get(wa_name="welcome_msg").pk
        req.return_value = FakeResp(200, {"id": "tpl-9", "status": "APPROVED", "category": "UTILITY"})
        self.assertEqual(self.admin_client.post(f"/api/admin/templates/{tpl_id}/sync/").data["wa_status"], "APPROVED")

        req.return_value = FakeResp(200, {"messages": [{"id": "wamid.1"}]})
        r = self.admin_client.post(f"/api/admin/templates/{tpl_id}/test/", {"to": "+91 99999 99999"}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        params = req.call_args.kwargs["json"]["template"]["components"][0]["parameters"]
        self.assertEqual(params[0]["text"], "Admin")
        self.assertEqual(req.call_args.kwargs["json"]["to"], "919999999999")

    def test_whatsapp_validation(self):
        trig = Trigger.objects.get(key="login")
        Template.objects.filter(trigger=trig, channel="whatsapp").delete()
        r = self.admin_client.post("/api/admin/templates/", {
            "trigger": trig.pk, "channel": "whatsapp", "wa_name": "Bad Name", "body": "{{name}} hi",
        }, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("wa_name", r.data)
        self.assertIn("body", r.data)

    @mock.patch("notifications.services.whatsapp.requests.request")
    def test_meta_error_keeps_template(self, req):
        req.return_value = FakeResp(401, {"error": {"code": 190, "message": "expired"}})
        tpl = Template.objects.get(trigger__key="login", channel="whatsapp")
        r = self.admin_client.patch(f"/api/admin/templates/{tpl.pk}/", {"body": "Hi {{first_name}}, new sign in."}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["wa_status"], "ERROR")
        self.assertIn("expired or revoked", r.data["notice"])

    def test_inactivity_fires_once_per_absence(self):
        self.register()
        user = User.objects.get(username="riya@example.com")
        self.admin_client.post(f"/api/admin/users/{user.pk}/simulate-inactive/", {"days": 8}, format="json")
        with mock.patch("notifications.services.webpush.requests.post", return_value=FakeResp(200, {"id": "x"})):
            fired = self.admin_client.post("/api/admin/run-inactivity-check/").data["fired"]
            self.assertEqual(sorted(f["trigger"] for f in fired if f["user"] == user.email), ["inactive_1d", "inactive_1w"])
            again = self.admin_client.post("/api/admin/run-inactivity-check/").data["fired"]
            self.assertEqual([f for f in again if f["user"] == user.email], [])
        body = NotificationLog.objects.get(trigger__key="inactive_1w", channel="email").rendered_body
        self.assertIn("8 days", body)

    def test_cron_endpoint_requires_secret(self):
        self.assertEqual(self.client.post("/api/cron/inactivity/").status_code, 403)
        r = self.client.post("/api/cron/inactivity/", HTTP_X_CRON_SECRET="s3cret")
        self.assertEqual(r.status_code, 200)

    def test_order_trigger_and_my_notifications(self):
        token = self.register()["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        with mock.patch("notifications.services.webpush.requests.post", return_value=FakeResp(200, {"id": "x"})):
            r = self.client.post("/api/events/order/", {}, format="json")
        self.assertTrue(r.data["order_id"].startswith("ORD-"))
        mine = self.client.get("/api/me/notifications/").data
        self.assertTrue(any(r.data["order_id"] in (m["rendered_title"] + m["rendered_body"]) for m in mine))

    def test_missing_phone_is_skipped_not_crashed(self):
        tpl = Template.objects.get(trigger__key="login", channel="whatsapp")
        tpl.wa_status, tpl.enabled = "APPROVED", True
        tpl.save()
        self.client.post("/api/auth/register/", {"name": "No Phone", "email": "np@example.com", "password": "secret123"}, format="json")
        with mock.patch("notifications.services.webpush.requests.post", return_value=FakeResp(200, {"id": "x"})):
            self.client.post("/api/auth/login/", {"email": "np@example.com", "password": "secret123"}, format="json")
        log = NotificationLog.objects.get(trigger__key="login", channel="whatsapp")
        self.assertEqual(log.status, "skipped")

    def test_overview_and_users(self):
        self.assertIn("providers", self.admin_client.get("/api/admin/overview/").data)
        self.assertEqual(self.admin_client.get("/api/admin/users/").status_code, 200)
        self.assertEqual(self.admin_client.get("/api/admin/logs/?q=admin").status_code, 200)
        self.assertEqual(self.admin_client.get("/api/admin/events/").status_code, 200)

    def test_last_seen_updates_with_token_auth(self):
        token = self.register()["token"]
        user = User.objects.get(username="riya@example.com")
        user.profile.last_seen = timezone.now() - timedelta(days=3)
        user.profile.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.client.get("/api/auth/me/")
        user.profile.refresh_from_db()
        self.assertLess(timezone.now() - user.profile.last_seen, timedelta(minutes=1))


@override_settings(NOTIFY_ASYNC=False, EMAIL_PROVIDER="console")
class SmallTests(TestCase):
    def setUp(self):
        call_command("seed_notifications", verbosity=0)
        self.admin = User.objects.get(username="admin@signalboard.dev")
        self.c = APIClient()
        self.c.force_authenticate(self.admin)

    def test_matrix_keeps_admin_order_with_counts(self):
        keys = [t["key"] for t in self.c.get("/api/admin/triggers/").data]
        self.assertEqual(keys, ["login", "logout", "inactive_1d", "inactive_1w", "password_reset", "order_placed"])

    def test_device_never_blank(self):
        from .renderer import build_context
        self.assertEqual(build_context(self.admin)["device"], "a browser")
        ua = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit Chrome/129 Safari/537"
        self.assertEqual(build_context(self.admin, {"device": ua})["device"], "Chrome on Windows")

    def test_custom_inactivity_trigger_needs_days(self):
        r = self.c.post("/api/admin/triggers/", {"key": "away_3d", "name": "Away 3 days", "kind": "inactivity"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/admin/triggers/", {"key": "away_3d", "name": "Away 3 days", "kind": "inactivity", "inactivity_days": 3}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["templates"], {"whatsapp": None, "email": None, "webpush": None})


@override_settings(
    WHATSAPP_ACCESS_TOKEN="tok", WHATSAPP_PHONE_NUMBER_ID="111", WHATSAPP_BUSINESS_ACCOUNT_ID="222",
    EMAIL_PROVIDER="postmark", POSTMARK_TOKEN="pm", POSTMARK_FROM_EMAIL="me@x.dev",
    ONESIGNAL_APP_ID="app", ONESIGNAL_REST_API_KEY="os_v2_app_key",
)
class VerifyChannelsTests(TestCase):
    def run_cmd(self, expires_at):
        from io import StringIO

        def fake_get(url, **kw):
            if url.endswith("/111"):
                return FakeResp(200, {"display_phone_number": "+1 555 0100", "verified_name": "Test"})
            if url.endswith("/debug_token"):
                return FakeResp(200, {"data": {"expires_at": expires_at}})
            if "message_templates" in url:
                return FakeResp(200, {"data": [{"name": "hello_world", "status": "APPROVED"}]})
            return FakeResp(200, {})

        out = StringIO()
        with mock.patch("notifications.management.commands.verify_channels.requests.get", side_effect=fake_get), \
             mock.patch("notifications.management.commands.verify_channels.requests.post", return_value=FakeResp(200, {"id": ""})):
            call_command("verify_channels", stdout=out)
        return out.getvalue()

    def test_permanent_token_detected(self):
        out = self.run_cmd(0)
        self.assertIn("never expires", out)
        self.assertIn("approved: hello_world", out)
        self.assertIn("All checks passed", out)

    def test_temporary_token_warned(self):
        self.assertIn("Temporary token", self.run_cmd(1893456000))
