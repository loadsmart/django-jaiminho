from django.db import models


class Event(models.Model):
    type = models.CharField(max_length=64)
    action = models.CharField(max_length=64)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
