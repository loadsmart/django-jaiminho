from django.db import models
from django.utils import timezone

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField


class Event(models.Model):
    type = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    payload = JSONField()
    encoder = models.CharField(max_length=255, null=True)
    function_signature = models.CharField(max_length=255, null=True)
    options = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)

    def mark_as_sent(self):
        self.sent_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Event(id={self.id}, type={self.type}, action={self.action}"
