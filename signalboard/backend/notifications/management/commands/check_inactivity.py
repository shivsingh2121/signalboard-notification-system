from django.core.management.base import BaseCommand

from notifications.inactivity import run_inactivity_check


class Command(BaseCommand):
    help = "Fire 'not logged in for N days' triggers. Schedule hourly (Render Cron Job)."

    def handle(self, *args, **opts):
        fired = run_inactivity_check()
        for f in fired:
            self.stdout.write(f"fired {f['trigger']} for {f['user']} ({f['days_inactive']} days)")
        self.stdout.write(self.style.SUCCESS(f"Done. {len(fired)} notification event(s)."))
