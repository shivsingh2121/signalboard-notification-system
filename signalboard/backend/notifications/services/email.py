"""Transactional email. Provider picked by EMAIL_PROVIDER (postmark | brevo | resend | console)."""
import html
import logging

import requests
from django.conf import settings

from . import NotConfigured, ProviderError

log = logging.getLogger(__name__)
TIMEOUT = 20


def provider():
    return settings.EMAIL_PROVIDER


def from_email():
    return {
        "postmark": settings.POSTMARK_FROM_EMAIL,
        "brevo": settings.BREVO_FROM_EMAIL,
        "resend": settings.RESEND_FROM_EMAIL,
    }.get(provider(), "console@localhost")


def is_configured():
    p = provider()
    if p == "console":
        return True
    key = {"postmark": settings.POSTMARK_TOKEN, "brevo": settings.BREVO_API_KEY, "resend": settings.RESEND_API_KEY}.get(p)
    return bool(key and from_email())


def build_html(subject, body, cta_label="", cta_url=""):
    paragraphs = "".join(
        f'<p style="margin:0 0 14px;line-height:1.6">{html.escape(p).replace(chr(10), "<br>")}</p>'
        for p in body.strip().split("\n\n") if p.strip()
    )
    button = ""
    if cta_label and cta_url:
        button = (
            f'<p style="margin:22px 0 6px"><a href="{html.escape(cta_url)}" '
            'style="background:#3538cd;color:#fff;text-decoration:none;padding:12px 20px;'
            f'border-radius:8px;font-weight:600;display:inline-block">{html.escape(cta_label)}</a></p>'
        )
    return f"""<!doctype html><html><body style="margin:0;background:#eef0f7;font-family:Segoe UI,Helvetica,Arial,sans-serif;color:#1c2140">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 12px"><tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:14px;overflow:hidden">
<tr><td style="background:#1c2140;color:#fff;padding:18px 28px;font-weight:700;font-size:17px">{html.escape(settings.SITE_NAME)}</td></tr>
<tr><td style="padding:28px">
<h1 style="font-size:20px;margin:0 0 18px">{html.escape(subject)}</h1>{paragraphs}{button}
</td></tr>
<tr><td style="padding:16px 28px;background:#f6f7fb;color:#6b7194;font-size:12px">You're receiving this because you have an account on {html.escape(settings.SITE_NAME)}.</td></tr>
</table></td></tr></table></body></html>"""


def _post(url, headers, payload):
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ProviderError(f"Could not reach {provider()}: {exc}") from exc
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:300]}
    if resp.status_code >= 400:
        msg = data.get("Message") or data.get("message") or data.get("raw") or str(data)
        raise ProviderError(f"{provider().title()} rejected the email: {msg}")
    return data


def send(to, subject, text, html_body):
    if not is_configured():
        raise NotConfigured(f"Email provider '{provider()}' is missing its API key or verified sender email in .env.")
    p = provider()
    sender = from_email()
    if p == "console":
        log.info("[console email] to=%s subject=%s\n%s", to, subject, text)
        return "console"
    if p == "postmark":
        data = _post(
            "https://api.postmarkapp.com/email",
            {"Accept": "application/json", "X-Postmark-Server-Token": settings.POSTMARK_TOKEN},
            {"From": sender, "To": to, "Subject": subject, "TextBody": text, "HtmlBody": html_body,
             "MessageStream": settings.POSTMARK_MESSAGE_STREAM},
        )
        return data.get("MessageID", "")
    if p == "brevo":
        data = _post(
            "https://api.brevo.com/v3/smtp/email",
            {"accept": "application/json", "api-key": settings.BREVO_API_KEY},
            {"sender": {"email": sender, "name": settings.SITE_NAME}, "to": [{"email": to}],
             "subject": subject, "htmlContent": html_body, "textContent": text},
        )
        return data.get("messageId", "")
    if p == "resend":
        data = _post(
            "https://api.resend.com/emails",
            {"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            {"from": f"{settings.SITE_NAME} <{sender}>", "to": [to], "subject": subject, "html": html_body, "text": text},
        )
        return data.get("id", "")
    raise NotConfigured(f"Unknown EMAIL_PROVIDER '{p}'. Use postmark, brevo, resend or console.")
