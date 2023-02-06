import logging
from abc import ABC, abstractmethod
import dill

from django.db import transaction

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
from jaiminho.relayer import EventRelayer
from jaiminho.signals import event_published, event_failed_to_publish, get_event_payload
from jaiminho import settings


logger = logging.getLogger(__name__)


def create_event_data(func_signature, args, kwargs, strategy, stream=None):
    return {
        "message": dill.dumps(args),
        "function": func_signature,
        "kwargs": dill.dumps(kwargs) if bool(kwargs) else None,
        "strategy": strategy,
        "stream": stream,
    }


class BaseStrategy(ABC):
    @abstractmethod
    def publish(self, args, kwargs, func, stream=None):
        raise NotImplementedError


class PublishOnCommitStrategy(BaseStrategy):
    def publish(self, args, kwargs, func, stream=None):
        func_signature = dill.dumps(func)
        event_data = create_event_data(
            func_signature,
            args,
            kwargs,
            PublishStrategyType.PUBLISH_ON_COMMIT,
            stream=stream,
        )

        event = None
        if settings.persist_all_events:
            event = Event.objects.create(**event_data)
            logger.info(
                f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {args}"
            )

        on_commit_hook_kwargs = {
            "func": func,
            "event_data": event_data,
            "event": event,
            "args": args,
            "kwargs": kwargs,
        }
        transaction.on_commit(lambda: on_commit_hook(**on_commit_hook_kwargs))
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: On commit hook configured. Event: {event}"
        )


class KeepOrderStrategy(BaseStrategy):
    def publish(self, args, kwargs, func, stream=None):
        func_signature = dill.dumps(func)
        event_data = create_event_data(
            func_signature,
            args,
            kwargs,
            PublishStrategyType.KEEP_ORDER,
            stream=stream,
        )
        event = Event.objects.create(**event_data)
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {args}"
        )


def create_publish_strategy(strategy_type):
    strategy_map = {
        PublishStrategyType.PUBLISH_ON_COMMIT: PublishOnCommitStrategy,
        PublishStrategyType.KEEP_ORDER: KeepOrderStrategy,
    }

    try:
        return strategy_map[strategy_type]()
    except KeyError as exc:
        raise ValueError(f"Unknow strategy type: {strategy_type}")


def on_commit_hook(func, event, event_data, args, kwargs):
    event_payload = get_event_payload(args)

    try:
        func(*args, **kwargs)
        logger.info(
            f"JAIMINHO-ON-COMMIT-HOOK: Event sent successfully. Payload: {args}"
        )

        event_published.send(
            sender=func, event_payload=event_payload, args=args, **kwargs
        )
    except BaseException as exc:
        if not event:
            event = Event.objects.create(**event_data)

        logger.warning(
            f"JAIMINHO-ON-COMMIT-HOOK: Event failed to be published. Event: {event}, Payload: {args}, "
            f"Exception: {exc}"
        )
        event_failed_to_publish.send(
            sender=func, event_payload=event_payload, args=args, **kwargs
        )
        return

    if event:
        if settings.delete_after_send:
            logger.info(
                f"JAIMINHO-ON-COMMIT-HOOK: Event deleted after success send. Event: {event}, Payload: {args}"
            )
            event.delete()
        else:
            logger.info(
                f"JAIMINHO-ON-COMMIT-HOOK: Event marked as sent. Event: {event}, Payload: {args}"
            )
            event.mark_as_sent()
