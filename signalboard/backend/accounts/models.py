from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    """Extra info we need to reach a user on each channel."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True, help_text="WhatsApp number with country code, digits only")
    push_subscription_id = models.CharField(max_length=100, blank=True, help_text="OneSignal web push subscription id")
    last_seen = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now, editable=False, help_text="When the profile was created (registration)")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last time phone / push details changed")

    def __str__(self):
        return f"Profile<{self.user.email}>"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.email.split("@")[0]