from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False, help_text="When the profile was created (registration)"),
        ),
        migrations.AddField(
            model_name="profile",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, help_text="Last time phone / push details changed"),
        ),
    ]