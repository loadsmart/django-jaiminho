from django.db import models
from django.utils import timezone

try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField


BYTES = 65535


class Event(models.Model):
    message = models.BinaryField(null=True, max_length=BYTES)
    function = models.BinaryField(null=True, max_length=BYTES)
    kwargs = models.BinaryField(null=True, max_length=BYTES)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)

    def mark_as_sent(self):
        self.sent_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Event(id={self.id})"
