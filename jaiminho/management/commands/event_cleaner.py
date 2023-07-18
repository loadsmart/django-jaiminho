import logging
from datetime import timedelta

from django.core.management import BaseCommand
from django.utils import timezone

from jaiminho import settings
from jaiminho.models import Event

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def __new__(cls, *args, **kwargs):
        assert isinstance(settings.time_to_delete, timedelta)
        return super().__new__(cls, *args, **kwargs)

    def handle(self, *args, **options):
        deletion_threshold_timestamp = timezone.now() - settings.time_to_delete

        events_to_delete = Event.objects.filter(sent_at__isnull=False).filter(
            sent_at__lt=deletion_threshold_timestamp
        )

        logger.info("JAIMINHO-EVENT-CLEANER: Start cleaning up events ..")

        count = events_to_delete._raw_delete(events_to_delete.db)

        logger.info(
            "JAIMINHO-EVENT-CLEANER: Successfully deleted %s events",
            count,
        )
