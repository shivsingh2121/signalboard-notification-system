"""Browser (Web Push) notifications through OneSignal's free tier."""
import requests
from django.conf import settings

from . import NotConfigured, ProviderError

TIMEOUT = 20
URL = "https://api.onesignal.com/notifications?c=push"


def is_configured():
    return bool(settings.ONESIGNAL_APP_ID and settings.ONESIGNAL_REST_API_KEY)


def _auth_header():
    key = settings.ONESIGNAL_REST_API_KEY
    # New-style keys (os_v2_...) use "Key", legacy keys use "Basic".
    return f"Key {key}" if key.startswith("os_v2") else f"Basic {key}"


def send(user, title, body, url=""):
    if not is_configured():
        raise NotConfigured("Set ONESIGNAL_APP_ID and ONESIGNAL_REST_API_KEY in the backend .env.")
    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "target_channel": "push",
        "headings": {"en": title},
        "contents": {"en": body},
    }
    if url:
        payload["web_url"] = url
    sub_id = getattr(getattr(user, "profile", None), "push_subscription_id", "")
    if sub_id:
        payload["include_subscription_ids"] = [sub_id]
    else:
        # Fallback: the frontend also calls OneSignal.login(<user id>)
        payload["include_aliases"] = {"external_id": [str(user.pk)]}

    try:
        resp = requests.post(URL, json=payload, timeout=TIMEOUT, headers={
            "Authorization": _auth_header(), "Content-Type": "application/json", "Accept": "application/json",
        })
    except requests.RequestException as exc:
        raise ProviderError(f"Could not reach OneSignal: {exc}") from exc
    try:
        data = resp.json()
    except ValueError:
        data = {"errors": [resp.text[:300]]}
    if resp.status_code >= 400 or not data.get("id"):
        errors = data.get("errors") or data
        if isinstance(errors, dict) and "invalid_player_ids" in errors:
            errors = "This browser subscription is no longer valid. Turn browser alerts off and on again."
        elif isinstance(errors, list):
            errors = "; ".join(map(str, errors))
        if "not subscribed" in str(errors).lower():
            errors = "This user hasn't allowed browser notifications yet. Open the website and turn on browser alerts."
        raise ProviderError(f"OneSignal: {errors}")
    return data["id"]
