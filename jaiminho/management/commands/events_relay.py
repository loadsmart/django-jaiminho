import argparse
import logging
from time import sleep

from django.core.management import BaseCommand
from jaiminho.relayer import EventRelayer


log = logging.getLogger(__name__)


class Command(BaseCommand):
    event_relayer = EventRelayer()

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-in-loop",
            type=bool,
            default=False,
            action=argparse.BooleanOptionalAction,
            help="Define if command should run in loop or just once",
        )
        parser.add_argument(
            "--loop-interval",
            nargs="?",
            type=float,
            default=1,
            help="Define the sleep interval (in seconds) between each loop"
        )
        parser.add_argument(
            "--stream",
            nargs="?",
            type=str,
            default=None,
            help="Define which stream events should be relayed. If not provided, all events will be relayed."
        )

    def handle(self, *args, **options):
        if options["run_in_loop"]:
            log.info("EVENTS-RELAY-COMMAND: Started to relay events in loop mode")

            while True:
                self.event_relayer.relay(stream=options["stream"])
                sleep(options["loop_interval"])
                log.info("EVENTS-RELAY-COMMAND: Relay iteration finished")

        else:
            log.info("EVENTS-RELAY-COMMAND: Started to relay events only once")
            self.event_relayer.relay(stream=options["stream"])
            log.info("EVENTS-RELAY-COMMAND: Relay finished")
