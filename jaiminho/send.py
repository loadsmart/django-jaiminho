import logging
from functools import wraps
from abc import ABC, abstractmethod
import dill

from django.db import transaction

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
from jaiminho.signals import event_published, event_failed_to_publish, \
    event_published_by_events_relay, event_failed_to_publish_by_events_relay
from jaiminho import settings

logger = logging.getLogger(__name__)


def _capture_exception(exception):
    capture_exception = settings.default_capture_exception
    if capture_exception:
        capture_exception(exception)


def _extract_original_func(event):
    fn = dill.loads(event.function)
    original_fn = getattr(fn, "original_func", fn)
    return original_fn


class BaseStrategy(ABC):
    @abstractmethod
    def publish(self, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def relay(self, **kwargs):
        pass


class EventRelayer:
    def __init__(self, stuck_on_error):
        self.stuck_on_error = stuck_on_error

    def relay(self):
        failed_events = Event.objects.filter(sent_at__isnull=True).order_by(
            "created_at"
        )

        if not failed_events:
            logger.info("No failed events found.")
            return

        for event in failed_events:
            message = dill.loads(event.message)
            kwargs = dill.loads(event.kwargs) if event.kwargs else {}
            try:
                original_fn = _extract_original_func(event)
                original_fn(message, **kwargs)
                logger.info(f"JAIMINHO-EVENTS-RELAY: Event sent. Event {event}")

                if settings.delete_after_send:
                    event.delete()
                    logger.info(
                        f"JAIMINHO-EVENTS-RELAY: Event deleted after success send. Event: {event}, Payload: {message}"
                    )
                else:
                    event.mark_as_sent()
                    logger.info(
                        f"JAIMINHO-EVENTS-RELAY: Event marked as sent. Event: {event}, Payload: {message}"
                    )

                event_published_by_events_relay.send(
                    sender=original_fn, event_payload=message
                )

            except (ModuleNotFoundError, AttributeError) as e:
                logger.warning(
                    f"JAIMINHO-EVENTS-RELAY: Function does not exist anymore, Event: {event} | Error: {str(e)}")
                _capture_exception(e)

            except Exception as e:
                logger.warning(
                    f"JAIMINHO-EVENTS-RELAY: An error occurred when relaying event: {event} | Error: {str(e)}")
                original_fn = _extract_original_func(event)
                event_failed_to_publish_by_events_relay.send(
                    sender=original_fn, event_payload=message
                )
                _capture_exception(e)


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
        # func_signature = dill.dumps(func)
        # event_data = {
        #     "message": dill.dumps(payload),
        #     "function": func_signature,
        #     "kwargs": dill.dumps(kwargs) if bool(kwargs) else None,
        # }
        #
        # event = Event.objects.create(**event_data)
        # logger.info(f"JAIMINHO-SAVE-TO-OUTBOX: Event created: Event {event}, Payload: {payload}")
        raise not NotImplementedError()

    def relay(self, **kwargs):
        # self.event_relayer.relay()
        raise not NotImplementedError()


def create_publish_strategy(strategy_type):
    strategy_map = {
        PublishStrategyType.PERFORMANCE: PerformanceStrategy
    }

    try:
        return strategy_map[strategy_type]()
    except KeyError:
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


def save_to_outbox(func):
    @wraps(func)
    def inner(payload, **kwargs):
        performance_strategy = create_publish_strategy(settings.publish_strategy)
        performance_strategy.publish(payload, kwargs, func)

    inner.original_func = func
    return inner
