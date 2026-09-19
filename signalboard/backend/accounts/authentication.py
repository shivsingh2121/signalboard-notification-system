from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import TokenAuthentication

from .models import Profile


class ActivityTokenAuthentication(TokenAuthentication):
    """Token auth ("Authorization: Token <key>") that also tracks last_seen.

    last_seen powers the "not logged in for N days" triggers. We only write
    it once a minute per user to keep the DB quiet.
    """

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        now = timezone.now()
        profile, _ = Profile.objects.get_or_create(user=user)
        if now - profile.last_seen > timedelta(minutes=1):
            Profile.objects.filter(pk=profile.pk).update(last_seen=now)
        return user, token
