from jaiminho.management.events_relay import RelayEventsCommand


class Command(RelayEventsCommand):
    def __init__(self):
        super(Command, self).__init__()
