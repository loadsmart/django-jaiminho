import sentry_sdk

from jaiminho.management.relay_events import RelayEventsCommand
from jaiminho_django_project.send import notify


class Command(RelayEventsCommand):
    notify_fn = notify
    capture_exception_fn = sentry_sdk.capture_exception()
