import logging
from abc import ABC, abstractmethod
import dill

from django.db import transaction

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
from jaiminho.relayer import EventRelayer
from jaiminho.signals import event_published, event_failed_to_publish
from jaiminho import settings


logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    @abstractmethod
    def publish(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def relay(self, **kwargs):
        raise NotImplementedError


class PerformanceStrategy(BaseStrategy):
    event_relayer = EventRelayer(stuck_on_error=False)

    def publish(self, payload, kwargs, func):
        func_signature = dill.dumps(func)
        event_data = {
            "message": dill.dumps(payload),
            "function": func_signature,
            "kwargs": dill.dumps(kwargs) if bool(kwargs) else None,
        }

        event = None
        if settings.persist_all_events:
            event = Event.objects.create(**event_data)
            logger.info(f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {payload}")

        on_commit_hook_kwargs = {
            "payload": payload,
            "func": func,
            "event_data": event_data,
            "event": event,
            **kwargs,
        }
        transaction.on_commit(lambda: on_commit_hook(**on_commit_hook_kwargs))
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: On commit hook configured. Event: {event}"
        )

    def relay(self, **kwargs):
        self.event_relayer.relay()


class KeepOrderStrategy(BaseStrategy):
    event_relayer = EventRelayer(stuck_on_error=True)

    def publish(self, payload, kwargs, func):
        func_signature = dill.dumps(func)
        event_data = {
            "message": dill.dumps(payload),
            "function": func_signature,
            "kwargs": dill.dumps(kwargs) if bool(kwargs) else None,
        }

        event = Event.objects.create(**event_data)
        logger.info(f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {payload}")

    def relay(self, **kwargs):
        self.event_relayer.relay()


def create_publish_strategy(strategy_type):
    strategy_map = {
        PublishStrategyType.PERFORMANCE: PerformanceStrategy,
        PublishStrategyType.KEEP_ORDER: KeepOrderStrategy
    }

    try:
        return strategy_map[strategy_type]()
    except KeyError as exc:
        raise ValueError(f"Unknow strategy type: {strategy_type}")


def on_commit_hook(payload, func, event, event_data, **kwargs):
    try:
        func(payload, **kwargs)
        logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event sent successfully. Payload: {payload}")
        event_published.send(sender=func, event_payload=payload)
    except BaseException as exc:
        if not event:
            event = Event.objects.create(**event_data)

        logger.warning(
            f"JAIMINHO-ON-COMMIT-HOOK: Event failed to be published. Event: {event}, Payload: {payload}, "
            f"Exception: {exc}"
        )
        event_failed_to_publish.send(sender=func, event_payload=payload)
        return

    if event:
        if settings.delete_after_send:
            logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event deleted after success send. Event: {event}, Payload: {payload}")
            event.delete()
        else:
            logger.info(f"JAIMINHO-ON-COMMIT-HOOK: Event marked as sent. Event: {event}, Payload: {payload}")
            event.mark_as_sent()
