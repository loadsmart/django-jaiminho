import logging
from functools import wraps
import dill

from django.db import transaction

from jaiminho.models import Event
from jaiminho.signals import event_published, event_failed_to_publish
from jaiminho import settings

logger = logging.getLogger(__name__)


def on_commit_hook(payload, func, event, event_data, **kwargs):
    try:
        func(payload, **kwargs)
        logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event sent successfully. Payload: {payload}")
        event_published.send(sender=func, event_payload=payload)
    except BaseException as exc:
        if not event:
            event = Event.objects.create(**event_data)

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
    func_signature = dill.dumps(func)

    @wraps(func)
    def inner(payload, **kwargs):
        event_data = {
            "message": dill.dumps(payload),
            "function": func_signature,
            "kwargs": dill.dumps(kwargs) if bool(kwargs) else None,
        }

        event = None
        if settings.persist_all_events:
            event = Event.objects.create(**event_data)
            logger.info(f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {payload}")

        on_commit_hook_kwargs = {
            "payload": payload,
            "func": func,
            "event_data": event_data,
            "event": event,
            **kwargs,
        }
        transaction.on_commit(lambda: on_commit_hook(**on_commit_hook_kwargs))
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: On commit hook configured. Event: {event}"
        )

    inner.original_func = func
    return inner
