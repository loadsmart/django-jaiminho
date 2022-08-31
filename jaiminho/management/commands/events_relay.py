import logging
from time import sleep

from django.core.management import BaseCommand

from jaiminho import settings
from jaiminho.send import create_publish_strategy

log = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "run_in_loop",
            nargs="?",
            type=bool,
            default=False,
            help="Define if command should run in loop or just once"
        )
        parser.add_argument(
            "loop_interval",
            nargs="?",
            type=float,
            default=1,
            help="Define the sleep interval (in seconds) between each loop"
        )
        parser.add_argument(
            "stream",
            nargs="?",
            type=str,
            default=None,
            help="Define which stream events should be relayed. If not provided, all events will be relayed."
        )

    def handle(self, *args, **options):
        publish_strategy = create_publish_strategy(settings.publish_strategy)

        if options["run_in_loop"]:
            log.info("EVENTS-RELAY-COMMAND: Started to relay events in loop mode")

            while True:
                publish_strategy.relay()
                sleep(options["loop_interval"])
                log.info("EVENTS-RELAY-COMMAND: Relay iteration finished")

        else:
            log.info("EVENTS-RELAY-COMMAND: Started to relay events only once")
            publish_strategy.relay(stream=options["stream"])
            log.info("EVENTS-RELAY-COMMAND: Relay finished")
