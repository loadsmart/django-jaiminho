import logging
from functools import wraps

from jaiminho.publish_strategies import create_publish_strategy
from jaiminho import settings


logger = logging.getLogger(__name__)


def save_to_outbox(func):
    @wraps(func)
    def inner(*args, **kwargs):
        publish_strategy = create_publish_strategy(settings.publish_strategy)
        publish_strategy.publish(args, kwargs, func)

    inner.original_func = func
    return inner


def save_to_outbox_stream(stream, overwrite_strategy_with=None):
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            _publish_strategy = (
                overwrite_strategy_with
                if overwrite_strategy_with
                else settings.publish_strategy
            )
            publish_strategy = create_publish_strategy(_publish_strategy)
            publish_strategy.publish(args, kwargs, func, stream)

        inner.original_func = func
        return inner

    return decorator
