import dill

from django.db import models
from django.utils import timezone
from django.core.signing import Signer, BadSignature

from jaiminho.constants import PublishStrategyType

MAX_BYTES = 65535


class Event(models.Model):
    id = models.BigAutoField(primary_key=True)
    message = models.BinaryField(null=True, max_length=MAX_BYTES)
    message_signing_key = models.CharField(null=True, max_length=255)
    function = models.BinaryField(null=True, max_length=MAX_BYTES)
    function_signing_key = models.CharField(null=True, max_length=255)
    kwargs = models.BinaryField(null=True, max_length=MAX_BYTES)
    kwargs_signing_key = models.CharField(null=True, max_length=255)
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
        if string is None:
            return None

        signer = self._signer()

        return self._signer().sign(string).split(signer.sep)[-1]

    def verify_integrity(self):
        signing_key_checks = [
            self._generate_signing_key(self.message) != self.message_signing_key,
            self._generate_signing_key(self.function) != self.function_signing_key,
            self._generate_signing_key(self.kwargs) != self.kwargs_signing_key,
        ]

        if any(signing_key_checks):
            raise BadSignature(f"{self} has been tampered")

    def save(self, *args, **kwargs):
        self.message_signing_key = self._generate_signing_key(self.message)
        self.function_signing_key = self._generate_signing_key(self.function)
        self.kwargs_signing_key = self._generate_signing_key(self.kwargs)

        super().save(*args, **kwargs)
