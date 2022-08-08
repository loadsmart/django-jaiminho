import logging
from functools import wraps

from django.db import transaction

from jaiminho.func_handler import format_func_path
from jaiminho.models import Event
from jaiminho.kwargs_handler import format_kwargs
from jaiminho.signals import event_published, event_failed_to_publish
from jaiminho import settings

logger = logging.getLogger(__name__)


def on_commit_hook(payload, encoder, func, event, event_data, **kwargs):
    try:
        func(payload, encoder=encoder, **kwargs)
        logger.info(
            f"JAIMINHO-ON-COMMIT-HOOK: Event sent successfully. Payload: {payload}"
        )
        event_published.send(sender=func, event_payload=payload)
    except BaseException as exc:
        if not event:
            event = Event.objects.create(
                type=event_data["type"],
                action=event_data["action"],
                payload=event_data["payload"],
                encoder=event_data["encoder"],
                function_signature=event_data["function_signature"],
                options=event_data["options"],
            )

        logger.warning(
            f"JAIMINHO-ON-COMMIT-HOOK: Event failed to be published. Event: {event}, Payload: {payload}, "
            f"Exception: {exc}"
        )
        event_failed_to_publish.send(sender=func, event_payload=payload)
        return

    if event:
        if settings.delete_after_send:
            logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event deleted after success send. Event: {event}, Payload: {payload}")
            event.delete()
        else:
            logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event marked as sent. Event: {event}, Payload: {payload}")
            event.mark_as_sent()


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

        event = None
        if settings.persist_all_events:
            event = Event.objects.create(
                type=type,
                action=action,
                payload=payload,
                encoder=encoder_path,
                function_signature=func_signature,
                options=options,
            )
            logger.info(
                f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {payload}"
            )

        on_commit_hook_kwargs = {
            "payload": payload,
            "encoder": encoder,
            "func": func,
            "event_data": {
                "type": type,
                "action": action,
                "payload": payload,
                "encoder": encoder_path,
                "function_signature": func_signature,
                "options": options,
            },
            "event": event,
            **kwargs,
        }
        transaction.on_commit(lambda: on_commit_hook(**on_commit_hook_kwargs))
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: On commit hook configured. Event: {event}"
        )

    inner.original_func = func
    return inner
