import logging

from django.core.management import BaseCommand
from django.utils import timezone

from jaiminho import settings
from jaiminho.func_handler import load_func_from_path
from jaiminho.kwargs_handler import load_kwargs
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
            try:
                original_fn = self._extract_original_func(event)
                encoder = load_func_from_path(event.encoder)
                original_fn(
                    event.payload, encoder=encoder, **load_kwargs(event.options)
                )
                event.sent_at = timezone.now()
                event.save()
                event_published_by_events_relay.send(
                    sender=original_fn, event_payload=event.payload
                )

            except (ModuleNotFoundError, AttributeError) as e:
                log.warning("Function does not exist anymore: %s", str(e))
                self._capture_exception(e)

            except Exception as e:
                log.warning(e)
                original_fn = self._extract_original_func(event)
                event_failed_to_publish_by_events_relay.send(
                    sender=original_fn, event_payload=event.payload
                )
                self._capture_exception(e)

    def _capture_exception(self, e):
        capture_exception = settings.default_capture_exception
        if capture_exception:
            capture_exception(e)

    def _extract_original_func(self, event):
        fn = load_func_from_path(event.function_signature)
        original_fn = getattr(fn, "original_func", fn)
        return original_fn
