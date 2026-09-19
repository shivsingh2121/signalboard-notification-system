"""WhatsApp Cloud API (Meta sandbox / test number).

Template lifecycle handled here so the admin never has to open Meta's site:
  create/edit -> POST /{WABA_ID}/message_templates  or  POST /{TEMPLATE_ID}
  sync        -> GET  /{TEMPLATE_ID}  (or search by name)
  send        -> POST /{PHONE_NUMBER_ID}/messages  (type=template)
"""
import logging

import requests
from django.conf import settings
from django.utils import timezone

from ..renderer import render, sample_context, to_positional
from . import NotConfigured, ProviderError

log = logging.getLogger(__name__)
TIMEOUT = 20


def _base():
    return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"


def _headers():
    return {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}


def is_configured():
    return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)


def templates_configured():
    return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_BUSINESS_ACCOUNT_ID)


def _error_text(resp):
    try:
        err = resp.json().get("error", {})
        msg = err.get("error_user_msg") or err.get("message") or resp.text
        if err.get("code") == 190:
            msg = ("WhatsApp access token is expired or revoked. Use a permanent System User token (Business Settings > System users > Generate new token > expiry Never) in WHATSAPP_ACCESS_TOKEN.")
        return msg
    except ValueError:
        return resp.text[:300]


def _request(method, url, **kw):
    try:
        resp = requests.request(method, url, headers=_headers(), timeout=TIMEOUT, **kw)
    except requests.RequestException as exc:
        raise ProviderError(f"Could not reach WhatsApp Cloud API: {exc}") from exc
    if resp.status_code >= 400:
        raise ProviderError(_error_text(resp))
    return resp.json()


def build_components(template):
    body, mapping = to_positional(template.body)
    samples = sample_context()
    body_component = {"type": "BODY", "text": body}
    if mapping:
        body_component["example"] = {"body_text": [[samples.get(v, v) for v in mapping]]}
    components = []
    if template.title:
        components.append({"type": "HEADER", "format": "TEXT", "text": template.title})
    components.append(body_component)
    if template.footer:
        components.append({"type": "FOOTER", "text": template.footer})
    return components, mapping


def _apply_remote(template, data):
    template.wa_template_id = str(data.get("id") or template.wa_template_id)
    status = (data.get("status") or template.wa_status).upper()
    template.wa_status = status if status in template.WAStatus.values else template.WAStatus.PENDING
    reason = data.get("rejected_reason") or ""
    template.wa_status_reason = "" if reason in ("", "NONE") else str(reason)
    if data.get("category"):
        template.wa_category = data["category"]
    template.wa_synced_at = timezone.now()


def submit(template):
    """Create the template in Meta, or push an edit if it already exists."""
    if not templates_configured():
        raise NotConfigured("Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID in the backend .env.")
    if template.wa_use_existing:
        return sync(template)

    components, mapping = build_components(template)
    template.variable_mapping = mapping
    if template.wa_template_id:
        data = _request("POST", f"{_base()}/{template.wa_template_id}", json={"components": components})
        if data.get("success"):
            template.wa_status = template.WAStatus.PENDING
            template.wa_status_reason = ""
            template.wa_synced_at = timezone.now()
    else:
        payload = {
            "name": template.wa_name,
            "language": template.wa_language,
            "category": template.wa_category,
            "components": components,
        }
        data = _request("POST", f"{_base()}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates", json=payload)
        _apply_remote(template, data)
    template.save()
    return template


def sync(template):
    """Pull the latest review status from Meta."""
    if not templates_configured():
        raise NotConfigured("Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID in the backend .env.")
    fields = "id,name,status,category,language,rejected_reason,components"
    if template.wa_template_id:
        data = _request("GET", f"{_base()}/{template.wa_template_id}", params={"fields": fields})
    else:
        found = _request(
            "GET", f"{_base()}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates",
            params={"name": template.wa_name, "fields": fields, "limit": 20},
        ).get("data", [])
        found = [t for t in found if t.get("name") == template.wa_name and t.get("language") == template.wa_language] or found
        if not found:
            raise ProviderError(f"No template named '{template.wa_name}' ({template.wa_language}) exists in Meta yet. Save the template to submit it.")
        data = found[0]
    _apply_remote(template, data)

    if template.wa_use_existing:
        # Mirror Meta's body text so the admin preview matches what users receive.
        remote_body = next((c.get("text", "") for c in data.get("components", []) if c.get("type") == "BODY"), "")
        if remote_body and not template.body.strip():
            template.body = remote_body
    template.save()
    return template


def send(template, to, ctx):
    if not is_configured():
        raise NotConfigured("Set WHATSAPP_ACCESS_TOKEN and PHONE_NUMBER_ID in the backend .env.")
    if template.wa_status != template.WAStatus.APPROVED:
        raise ProviderError(
            f"WhatsApp template '{template.wa_name}' is {template.get_wa_status_display().lower()}. "
            "Meta only delivers approved templates — press Sync until it shows Approved."
        )
    tpl = {"name": template.wa_name, "language": {"code": template.wa_language}}
    if template.variable_mapping:
        tpl["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": str(ctx.get(v, "")) or "-"} for v in template.variable_mapping],
        }]
    payload = {"messaging_product": "whatsapp", "to": to, "type": "template", "template": tpl}
    data = _request("POST", f"{_base()}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages", json=payload)
    msgs = data.get("messages") or [{}]
    return msgs[0].get("id", "")


def delete_remote(template):
    if not (templates_configured() and template.wa_template_id and not template.wa_use_existing):
        return
    try:
        _request("DELETE", f"{_base()}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates",
                 params={"name": template.wa_name, "hsm_id": template.wa_template_id})
    except ProviderError as exc:  # not fatal — local delete still proceeds
        log.warning("Could not delete WhatsApp template %s: %s", template.wa_name, exc)


def preview_text(template, ctx):
    return render(template.body, ctx)
