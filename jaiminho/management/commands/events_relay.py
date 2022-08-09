import logging
import dill as pickle

from django.core.management import BaseCommand

from jaiminho import settings
from jaiminho.models import Event
from jaiminho.signals import (
    event_published_by_events_relay,
    event_failed_to_publish_by_events_relay,
)

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        failed_events = Event.objects.filter(sent_at__isnull=True).order_by(
            "created_at"
        )

        if not failed_events:
            log.info("No failed events found.")
            return

        for event in failed_events:
            message = pickle.loads(event.message)
            kwargs = pickle.loads(event.kwargs) if event.kwargs else {}
            try:
                original_fn = self._extract_original_func(event)
                original_fn(message, **kwargs)
                log.info(f"JAIMINHO-EVENTS-RELAY: Event sent. Event {event}")

                if settings.delete_after_send:
                    event.delete()
                    log.info(
                        f"JAIMINHO-EVENTS-RELAY: Event deleted after success send. Event: {event}, Payload: {message}"
                    )
                else:
                    event.mark_as_sent()
                    log.info(
                        f"JAIMINHO-EVENTS-RELAY: Event marked as sent. Event: {event}, Payload: {message}"
                    )

                event_published_by_events_relay.send(
                    sender=original_fn, event_payload=message
                )

            except (ModuleNotFoundError, AttributeError) as e:
                log.warning(f"JAIMINHO-EVENTS-RELAY: Function does not exist anymore, Event: {event} | Error: {str(e)}")
                self._capture_exception(e)

            except Exception as e:
                log.warning(f"JAIMINHO-EVENTS-RELAY: An error occurred when relaying event: {event} | Error: {str(e)}")
                original_fn = self._extract_original_func(event)
                event_failed_to_publish_by_events_relay.send(
                    sender=original_fn, event_payload=message
                )
                self._capture_exception(e)

    def _capture_exception(self, exception):
        capture_exception = settings.default_capture_exception
        if capture_exception:
            capture_exception(exception)

    def _extract_original_func(self, event):
        fn = pickle.loads(event.function)
        original_fn = getattr(fn, "original_func", fn)
        return original_fn
