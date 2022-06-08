import logging

from django.core.management import BaseCommand
from django.utils import timezone

from jaiminho import settings
from jaiminho.func_handler import load_func_from_path
from jaiminho.kwargs_handler import load_kwargs
from jaiminho.models import Event

log = logging.getLogger(__name__)


class RelayEventsCommand(BaseCommand):
    capture_exception_fn = settings.default_capture_exception

    def handle(self, *args, **options):
        failed_events = Event.objects.filter(sent_at__isnull=True).order_by(
            "created_at"
        )

        if not failed_events:
            log.info("No failed events found.")
            return

        for event in failed_events:
            try:
                fn = load_func_from_path(event.function_signature)
                original_fn = getattr(fn, "original_func", fn)
                encoder = load_func_from_path(event.encoder)
                original_fn(
                    event.payload, encoder=encoder, **load_kwargs(event.options)
                )
                event.sent_at = timezone.now()
                event.save()

            except (ModuleNotFoundError, AttributeError) as e:
                log.warning("Function does not exist anymore: %s", str(e))
                if self.capture_exception_fn:
                    self.capture_exception_fn(e)

            except Exception as e:
                log.warning(e)
                if self.capture_exception_fn:
                    self.capture_exception_fn(e)
