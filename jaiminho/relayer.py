import logging
import dill

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
from jaiminho.signals import (
    event_published_by_events_relay,
    event_failed_to_publish_by_events_relay,
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
        events_qs = Event.objects.filter(sent_at__isnull=True)
        events_qs = events_qs.filter(stream=stream)

        events_qs = events_qs.order_by("created_at")

        if not events_qs:
            logger.info("No failed events found.")
            return

        for event in events_qs:
            args = dill.loads(event.message)
            kwargs = dill.loads(event.kwargs) if event.kwargs else {}
            event_payload = get_event_payload(args)

            try:
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

                event_published_by_events_relay.send(
                    sender=original_fn, event_payload=event_payload, args=args, **kwargs
                )

            except (ModuleNotFoundError, AttributeError) as e:
                logger.warning(
                    f"JAIMINHO-EVENTS-RELAY: Function does not exist anymore, Event: {event} | Error: {str(e)}"
                )
                _capture_exception(e)

                if self.__stuck_on_error(event):
                    logger.warning(
                        f"JAIMINHO-EVENTS-RELAY: Events relaying are stuck due to failing Event: {event}"
                    )
                    return

            except BaseException as e:
                logger.warning(
                    f"JAIMINHO-EVENTS-RELAY: An error occurred when relaying event: {event} | Error: {str(e)}"
                )
                original_fn = _extract_original_func(event)
                event_failed_to_publish_by_events_relay.send(
                    sender=original_fn, event_payload=event_payload, args=args, **kwargs
                )
                _capture_exception(e)

                if self.__stuck_on_error(event):
                    logger.warning(
                        f"JAIMINHO-EVENTS-RELAY: Events relaying are stuck due to failing Event: {event}"
                    )
                    return

    def __stuck_on_error(self, event):
        if not event.strategy:
            return settings.publish_strategy == PublishStrategyType.KEEP_ORDER
        return event.strategy == PublishStrategyType.KEEP_ORDER
