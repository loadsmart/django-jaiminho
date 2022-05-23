import logging
from functools import wraps

from django.utils import timezone

from jaiminho.models import Event
from jaiminho.kwargs_handler import format_kwargs
from jaiminho import settings

logger = logging.getLogger(__name__)


def save_to_outbox(func):
    func_signature = f"{func.__module__}.{func.__name__}" if func else None

    @wraps(func)
    def inner(payload, encoder=None, **kwargs):
        type = payload.get("type")
        action = payload.get("action")
        options = format_kwargs(**kwargs)
        encoder = f"{encoder.__module__}.{encoder.__name__}" if encoder else None
        try:
            result = func(payload, **kwargs)
            if settings.persist_all_events:
                Event.objects.create(
                    type=type,
                    action=action,
                    payload=payload,
                    encoder=encoder,
                    sent_at=timezone.now(),
                    function_signature=func_signature,
                    options=options,
                )
        except Exception:
            Event.objects.create(
                type=type,
                action=action,
                payload=payload,
                encoder=encoder,
                function_signature=func_signature,
                options=options,
            )
            raise
        return result

    return inner
