import sentry_sdk

from jaiminho.management.relay_events import RelayEventsCommand


class Command(RelayEventsCommand):
    def __init__(self):
        super(Command, self).__init__()
