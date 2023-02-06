import logging

from django.dispatch import receiver
import jaiminho.signals


def log_metric(name, event_payload, **kwargs):
    logging.info("%s: %s", name, event_payload)


@receiver(jaiminho.signals.event_published)
def on_event_published(signal, sender, event_payload, **kwargs):
    log_metric("event-published", event_payload, **kwargs)


@receiver(jaiminho.signals.event_failed_to_publish)
def on_event_not_published(signal, sender, event_payload, **kwargs):
    log_metric("event-failed-to-publish", event_payload, **kwargs)


@receiver(jaiminho.signals.event_published_by_events_relay)
def on_event_published_through_relay_command(signal, sender, event_payload, **kwargs):
    log_metric("event-published-through-outbox", event_payload, **kwargs)


@receiver(jaiminho.signals.event_failed_to_publish_by_events_relay)
def on_event_not_published_through_relay_command(
    signal, sender, event_payload, **kwargs
):
    log_metric("event-failed-to-publish-through-outbox", event_payload, **kwargs)
