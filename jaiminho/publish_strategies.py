import logging
from abc import ABC, abstractmethod
from functools import partial

import dill

from django.db import transaction

from jaiminho.constants import PublishStrategyType
from jaiminho.errors import is_non_retryable
from jaiminho.models import Event
from jaiminho.signals import (
    event_published,
    event_failed_to_publish,
    event_permanently_failed,
    get_event_payload,
)
from jaiminho import settings

logger = logging.getLogger(__name__)


def create_event_data(func, args, kwargs, strategy, stream=None):
    args_dump = dill.dumps(args)
    func_dump = dill.dumps(func)
    kwargs_dump = dill.dumps(kwargs) if bool(kwargs) else None

    return {
        "message": args_dump,
        "function": func_dump,
        "kwargs": kwargs_dump,
        "strategy": strategy,
        "stream": stream,
    }


class BaseStrategy(ABC):
    @abstractmethod
    def publish(self, args, kwargs, func, stream=None, using=None):
        raise NotImplementedError


class PublishOnCommitStrategy(BaseStrategy):
    def publish(self, args, kwargs, func, stream=None, using=None):
        event_data = create_event_data(
            func,
            args,
            kwargs,
            PublishStrategyType.PUBLISH_ON_COMMIT,
            stream=stream,
        )

        event = None
        if settings.persist_all_events:
            event = Event.objects.using(using).create(**event_data)
            logger.info(
                f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {args}"
            )

        on_commit_hook_kwargs = {
            "func": func,
            "event_data": event_data,
            "event": event,
            "args": args,
            "kwargs": kwargs,
            "using": using,
        }
        transaction.on_commit(
            partial(on_commit_hook, **on_commit_hook_kwargs), using=using
        )
        logger.info(
            f"JAIMINHO-SAVE-TO-OUTBOX: On commit hook configured. Event: {event}"
        )


class KeepOrderStrategy(BaseStrategy):
    def publish(self, args, kwargs, func, stream=None, using=None):
        event_data = create_event_data(
            func,
            args,
            kwargs,
            PublishStrategyType.KEEP_ORDER,
            stream=stream,
        )
        event = Event.objects.using(using).create(**event_data)
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


def on_commit_hook(func, event, event_data, args, kwargs, using=None):
    event_payload = get_event_payload(args)

    try:
        func(*args, **kwargs)
        logger.info(
            f"JAIMINHO-ON-COMMIT-HOOK: Event sent successfully. Payload: {args}"
        )
    except BaseException as exc:
        if is_non_retryable(exc):
            if event:
                event.delete()

            logger.warning(
                f"JAIMINHO-ON-COMMIT-HOOK: Non-retryable error, event will not be retried. Payload: {args}, "
                f"Exception: {exc}"
            )
            event_permanently_failed.send(sender=func, event_payload=event_payload)
            return

        if not event:
            event = Event.objects.using(using).create(**event_data)

        logger.warning(
            f"JAIMINHO-ON-COMMIT-HOOK: Event failed to be published. Event: {event}, Payload: {args}, "
            f"Exception: {exc}"
        )
        event_failed_to_publish.send(sender=func, event_payload=event_payload)
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

    event_published.send(sender=func, event_payload=event_payload)
