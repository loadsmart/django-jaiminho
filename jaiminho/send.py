import logging
from functools import wraps

from jaiminho.publish_strategies import create_publish_strategy
from jaiminho import settings


logger = logging.getLogger(__name__)


def save_to_outbox(func):
    @wraps(func)
    def inner(payload, **kwargs):
        performance_strategy = create_publish_strategy(settings.publish_strategy)
        performance_strategy.publish(payload, kwargs, func)

    inner.original_func = func
    return inner
