import logging

from datetime import timedelta
from django.core.management import BaseCommand
from django.utils import timezone
from django.core.paginator import Paginator

from jaiminho import settings
from jaiminho.models import Event

logger = logging.getLogger(__name__)


def chunked_iterator(queryset, chunk_size=500):
    paginator = Paginator(queryset, chunk_size)
    for page in range(1, paginator.num_pages + 1):
        for item in paginator.page(page).object_list:
            yield item


class Command(BaseCommand):
    def __new__(cls, *args, **kwargs):
        assert isinstance(settings.time_to_delete, timedelta)
        return super().__new__(cls, *args, **kwargs)

    def handle(self, *args, **options):
        deletion_threshold_timestamp = timezone.now() - settings.time_to_delete

        events_to_delete = Event.objects.filter(sent_at__isnull=False).filter(
            sent_at__lt=deletion_threshold_timestamp
        )

        logger.info(
            "JAIMINHO-EVENT-CLEANER: Start cleaning up events .."
        )

        for event in chunked_iterator(events_to_delete):
            event.delete()

        logger.info(
            "JAIMINHO-EVENT-CLEANER: Successfully deleted %s events",
            len(events_to_delete),
        )
