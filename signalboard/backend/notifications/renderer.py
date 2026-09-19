"""{{variable}} rendering shared by all channels."""
import re

from django.conf import settings
from django.utils import timezone

VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

# name -> (description, sample value used for previews and Meta's required examples)
VARIABLES = {
    "name": ("User's full name", "Aman Raj"),
    "first_name": ("User's first name", "Aman"),
    "email": ("User's email", "aman@example.com"),
    "site_name": ("Website name", "Signalboard"),
    "site_url": ("Website address", "https://signalboard.vercel.app"),
    "date": ("Today's date", "18 Sep 2026"),
    "time": ("Current time", "10:30 AM"),
    "device": ("Browser that triggered it", "Chrome on Windows"),
    "order_id": ("Order number (Order placed)", "ORD-1042"),
    "order_total": ("Order amount (Order placed)", "₹1,499"),
    "reset_link": ("Password reset link", "https://signalboard.vercel.app/login?reset=demo"),
    "days_inactive": ("Days since last visit (inactivity)", "7"),
}


def sample_context():
    return {k: v[1] for k, v in VARIABLES.items()}


def build_context(user=None, extra=None):
    now = timezone.localtime()
    ctx = {
        "site_name": settings.SITE_NAME,
        "site_url": settings.FRONTEND_URL,
        "date": now.strftime("%d %b %Y"),
        "time": now.strftime("%I:%M %p").lstrip("0"),
    }
    if user is not None:
        full = user.get_full_name() or user.email.split("@")[0]
        ctx.update({"name": full, "first_name": user.first_name or full.split(" ")[0], "email": user.email})
    for k, v in (extra or {}).items():
        ctx[k] = "" if v is None else str(v)
    ctx["device"] = describe_device(ctx.get("device", "")) or "a browser"
    return ctx


def describe_device(ua):
    if not ua or " on " in ua:
        return ua
    browser = next((b for b in ("Edg", "OPR", "Chrome", "Firefox", "Safari") if b in ua), "a browser")
    browser = {"Edg": "Edge", "OPR": "Opera"}.get(browser, browser)
    os_name = next((o for o in ("Windows", "Android", "iPhone", "Mac OS", "Linux") if o in ua), "")
    os_name = {"Mac OS": "macOS"}.get(os_name, os_name)
    return f"{browser} on {os_name}" if os_name else browser


def render(text, ctx):
    return VAR_RE.sub(lambda m: str(ctx.get(m.group(1), "")), text or "")


def find_variables(text):
    """Variables in order of first appearance, de-duplicated."""
    seen = []
    for m in VAR_RE.finditer(text or ""):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def to_positional(text):
    """'Hi {{name}}, welcome to {{site_name}}' -> ('Hi {{1}}, welcome to {{2}}', ['name', 'site_name']).

    WhatsApp templates need numbered placeholders; we keep the mapping so we
    can fill them from our named variables at send time.
    """
    mapping = find_variables(text)
    positional = VAR_RE.sub(lambda m: "{{%d}}" % (mapping.index(m.group(1)) + 1), text or "")
    return positional, mapping
