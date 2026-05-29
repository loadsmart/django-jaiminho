from django.contrib import admin

from jaiminho.models import Event


class EventAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    fields = ("id", "signature", "sent_at", "stream", "strategy", "created_at")
    list_display = ("id", "signature", "sent_at", "stream", "strategy", "created_at")
    readonly_fields = (
        "id",
        "message",
        "function",
        "kwargs",
        "signature",
        "sent_at",
        "stream",
        "strategy",
        "created_at",
    )


admin.site.register(Event, EventAdmin)
