from jaiminho.management.event_cleaner import EventCleanerCommand


class Command(EventCleanerCommand):
    def __init__(self):
        super(Command, self).__init__()
