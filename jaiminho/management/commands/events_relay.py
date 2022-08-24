import logging

from django.core.management import BaseCommand

from jaiminho import settings
from jaiminho.send import create_publish_strategy

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        publish_strategy = create_publish_strategy(settings.publish_strategy)
        publish_strategy.relay()
