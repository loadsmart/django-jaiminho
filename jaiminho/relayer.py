import logging
import dill

from django.core.signing import BadSignature
from django.db import transaction

from jaiminho.constants import PublishStrategyType
from jaiminho.errors import is_non_retryable
from jaiminho.models import Event
from jaiminho.signals import (
    event_published_by_events_relay,
    event_failed_to_publish_by_events_relay,
    event_permanently_failed_by_events_relay,
    get_event_payload,
)
from jaiminho import settings

logger = logging.getLogger(__name__)


def _capture_exception(exception):
    capture_exception = settings.default_capture_exception
    if capture_exception:
        capture_exception(exception)


def _extract_original_func(event):
    fn = dill.loads(event.function)
    original_fn = getattr(fn, "original_func", fn)
    return original_fn


class EventRelayer:
    def relay(self, stream=None):
        skip_locked = settings.publish_strategy == PublishStrategyType.PUBLISH_ON_COMMIT
        events_qs = Event.objects.filter(sent_at__isnull=True)
        events_qs = events_qs.filter(stream=stream)

        events_qs = events_qs.order_by("created_at")

        if not events_qs:
            logger.info("No failed events found.")
            return

        for event in events_qs:
            event_id = event.id
            event_payload = {}

            with transaction.atomic():
                try:
                    event = (
                        Event.objects.select_for_update(skip_locked=skip_locked)
                        .filter(sent_at__isnull=True, id=event.id)
                        .first()
                    )

                    if not event:
                        logger.info(
                            f"JAIMINHO-EVENTS-RELAY: Event {event_id} already handled by another worker, skipping."
                        )
                        continue

                    event.verify_integrity()
                    args = dill.loads(event.message)
                    kwargs = dill.loads(event.kwargs) if event.kwargs else {}
                    event_payload = get_event_payload(args)

                    original_fn = _extract_original_func(event)
                    if isinstance(args, tuple):
                        original_fn(*args, **kwargs)
                    else:
                        original_fn(args, **kwargs)

                    logger.info(f"JAIMINHO-EVENTS-RELAY: Event sent. Event {event}")

                    if settings.delete_after_send:
                        event.delete()
                        logger.info(
                            f"JAIMINHO-EVENTS-RELAY: Event deleted after success send. Event: {event}, Payload: {args}"
                        )
                    else:
                        event.mark_as_sent()
                        logger.info(
                            f"JAIMINHO-EVENTS-RELAY: Event marked as sent. Event: {event}, Payload: {args}"
                        )

                    transaction.on_commit(
                        lambda: event_published_by_events_relay.send(
                            sender=original_fn, event_payload=event_payload
                        )
                    )
                except BadSignature as exception:
                    logger.warning(
                        f"JAIMINHO-EVENTS-RELAY: Event has been tampered, Event: {event}"
                    )
                    _capture_exception(exception)

                    if self.__give_up_on_non_retryable(event, exception, event_payload):
                        continue

                    if self.__stuck_on_error(event):
                        self.__warn_stuck_on_error(event)
                        return

                except (ModuleNotFoundError, AttributeError) as e:
                    logger.warning(
                        f"JAIMINHO-EVENTS-RELAY: Function does not exist anymore, Event: {event} | Error: {str(e)}"
                    )
                    _capture_exception(e)

                    if self.__give_up_on_non_retryable(event, e, event_payload):
                        continue

                    if self.__stuck_on_error(event):
                        self.__warn_stuck_on_error(event)
                        return

                except BaseException as e:
                    logger.warning(
                        f"JAIMINHO-EVENTS-RELAY: An error occurred when relaying event: {event} | Error: {str(e)}"
                    )
                    _capture_exception(e)

                    if self.__give_up_on_non_retryable(event, e, event_payload):
                        continue

                    original_fn = _extract_original_func(event)
                    transaction.on_commit(
                        lambda: event_failed_to_publish_by_events_relay.send(
                            sender=original_fn, event_payload=event_payload
                        )
                    )

                    if self.__stuck_on_error(event):
                        self.__warn_stuck_on_error(event)
                        return

    def __give_up_on_non_retryable(self, event, exception, event_payload):
        if not is_non_retryable(exception):
            return False

        try:
            original_fn = _extract_original_func(event)
        except BaseException:
            original_fn = None

        transaction.on_commit(
            lambda: event_permanently_failed_by_events_relay.send(
                sender=original_fn, event_payload=event_payload
            )
        )
        logger.warning(
            f"JAIMINHO-EVENTS-RELAY: Non-retryable error, event will not be retried. Event: {event}"
        )
        event.delete()
        return True

    def __stuck_on_error(self, event):
        if not event.strategy:
            return settings.publish_strategy == PublishStrategyType.KEEP_ORDER
        return event.strategy == PublishStrategyType.KEEP_ORDER

    def __warn_stuck_on_error(self, event):
        logger.warning(
            f"JAIMINHO-EVENTS-RELAY: Events relaying are stuck due to failing Event: {event}"
        )
