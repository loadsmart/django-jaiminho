import logging
from functools import wraps

from django.utils import timezone

from jaiminho.func_handler import format_func_path
from jaiminho.models import Event
from jaiminho.kwargs_handler import format_kwargs
from jaiminho.signals import event_published, event_failed_to_publish
from jaiminho import settings

logger = logging.getLogger(__name__)


def save_to_outbox(func):
    func_signature = format_func_path(func)

    @wraps(func)
    def inner(payload, encoder=None, **kwargs):
        if encoder is None:
            encoder = settings.default_encoder
        type = payload.get("type")
        action = payload.get("action")
        options = format_kwargs(**kwargs)
        encoder_path = format_func_path(encoder)
        try:
            result = func(payload, encoder=encoder, **kwargs)
            event_published.send(sender=func, event_payload=payload)
            if settings.persist_all_events:
                Event.objects.create(
                    type=type,
                    action=action,
                    payload=payload,
                    encoder=encoder_path,
                    sent_at=timezone.now(),
                    function_signature=func_signature,
                    options=options,
                )
        except Exception:
            Event.objects.create(
                type=type,
                action=action,
                payload=payload,
                encoder=encoder_path,
                function_signature=func_signature,
                options=options,
            )
            event_failed_to_publish.send(sender=func, event_payload=payload)
            if settings.raise_on_publishing_error:
                raise
            return

        return result

    inner.original_func = func
    return inner
