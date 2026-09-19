from django.contrib import admin

from .models import NotificationLog, Template, Trigger, TriggerEvent


class TemplateInline(admin.TabularInline):
    model = Template
    extra = 0
    fields = ("channel", "enabled", "title", "wa_name", "wa_status")


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "kind", "inactivity_days", "is_active")
    inlines = [TemplateInline]


@admin.register(NotificationLog)
class LogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "trigger", "channel", "recipient", "status", "is_test")
    list_filter = ("channel", "status", "is_test")


admin.site.register(TriggerEvent)
admin.site.site_header = "Signalboard (raw data)"
