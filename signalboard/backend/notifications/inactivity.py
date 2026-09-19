"""Fires inactivity triggers ("not logged in for N days")."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .dispatcher import fire_trigger
from .models import Trigger, TriggerEvent


def run_inactivity_check(run_async=False):
    """Each inactivity trigger fires at most once per absence per user:
    if we've already fired it since the user was last seen, we skip them."""
    User = get_user_model()
    now = timezone.now()
    fired = []
    for trigger in Trigger.objects.filter(kind=Trigger.Kind.INACTIVITY, is_active=True, inactivity_days__isnull=False):
        cutoff = now - timedelta(days=trigger.inactivity_days)
        users = User.objects.filter(is_active=True, profile__last_seen__lte=cutoff).select_related("profile")
        for user in users:
            already = TriggerEvent.objects.filter(
                trigger=trigger, user=user, created_at__gte=user.profile.last_seen
            ).exists()
            if already:
                continue
            days = (now - user.profile.last_seen).days
            fire_trigger(trigger.key, user, {"days_inactive": days}, run_async=run_async)
            fired.append({"trigger": trigger.key, "user": user.email, "days_inactive": days})
    return fired
