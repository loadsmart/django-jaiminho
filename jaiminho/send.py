import logging
from functools import wraps

from django.utils import timezone

from jaiminho.models import Event
from jaiminho.kwargs_handler import format_kwargs
from jaiminho import settings

logger = logging.getLogger(__name__)


def save_to_outbox(func):
    @wraps(func)
    def inner(payload, **kwargs):
        type = payload.get("type")
        action = payload.get("action")
        options = format_kwargs(**kwargs)
        try:
            result = func(payload, **kwargs)
            if settings.persist_all_events:
                Event.objects.create(
                    type=type,
                    action=action,
                    payload=payload,
                    sent_at=timezone.now(),
                    options=options,
                )
        except Exception:
            Event.objects.create(
                type=type,
                action=action,
                payload=payload,
                options=options,
            )
            raise
        return result

    return inner
