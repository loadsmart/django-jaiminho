import dill

from django.db import models
from django.utils import timezone
from django.core.signing import Signer, BadSignature

from jaiminho.constants import PublishStrategyType
from jaiminho import settings

MAX_BYTES = 65535


class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    message = models.BinaryField(null=True, max_length=MAX_BYTES)
    function = models.BinaryField(null=True, max_length=MAX_BYTES)
    kwargs = models.BinaryField(null=True, max_length=MAX_BYTES)
    signing_key = models.CharField(null=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    stream = models.CharField(max_length=100, null=True)
    strategy = models.CharField(
        max_length=100, null=True, choices=PublishStrategyType.CHOICES
    )

    def mark_as_sent(self):
        self.sent_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Event(id={self.id})"

    @staticmethod
    def _signer():
        return Signer()

    def _generate_signing_key(self, string):
        signer = self._signer()

        if string is None:
            return None

        return signer.sign(string).split(signer.sep)[-1]

    def _generate_event_signing_key(self):
        if not settings.sign_events:
            return None

        payload_to_sign = [
            value
            for value in [self.message, self.function, self.kwargs]
            if value is not None
        ]
        blob = b"".join(payload_to_sign)

        return self._generate_signing_key(blob) if blob else None

    def verify_integrity(self):
        current_signing_key = self._generate_event_signing_key()

        if not settings.verify_events_signature:
            return

        if current_signing_key != self.signing_key:
            raise BadSignature(f"{self} has been tampered")

    def save(self, *args, **kwargs):
        self.signing_key = self._generate_event_signing_key()

        super().save(*args, **kwargs)
