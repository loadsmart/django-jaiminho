import logging
import inspect
from functools import wraps

from django.utils import timezone

from jaiminho.models import Event
from jaiminho import settings

logger = logging.getLogger(__name__)

EXPECTED_PARAMETERS = {"type", "action", "payload"}


def save_to_outbox(func):
    assert set(inspect.signature(func).parameters) == EXPECTED_PARAMETERS

    @wraps(func)
    def inner(type, action, payload):
        try:
            result = func(type, action, payload)
            if settings.persist_all_events:
                Event.objects.create(type=type, action=action, payload=payload, sent_at=timezone.now())
        except Exception:
            Event.objects.create(type=type, action=action, payload=payload)
            raise
        return result
    return inner
