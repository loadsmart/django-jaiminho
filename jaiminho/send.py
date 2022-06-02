import logging
from functools import wraps

from django.utils import timezone

from jaiminho.models import Event
from jaiminho.kwargs_handler import format_kwargs
from jaiminho.signals import event_published, event_failed_to_publish
from jaiminho import settings

logger = logging.getLogger(__name__)


def save_to_outbox(func):
    func_signature = f"{func.__module__}.{func.__name__}" if func else None

    @wraps(func)
    def inner(payload, encoder=None, **kwargs):
        type = payload.get("type")
        action = payload.get("action")
        options = format_kwargs(**kwargs)
        encoder = f"{encoder.__module__}.{encoder.__name__}" if encoder else settings.default_encoder
        try:
            result = func(payload, **kwargs)
            event_published.send(sender=func, instance=payload)
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
            event_failed_to_publish.send(sender=func, instance=payload)
            raise
        return result

    return inner
