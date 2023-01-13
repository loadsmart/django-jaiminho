import json

from jaiminho.constants import PublishStrategyType
from jaiminho.send import save_to_outbox, save_to_outbox_stream


EXAMPLE_STREAM = "my-stream"


class InternalDecoder:
    def __call__(self, *args, **kwargs):
        print("Hello Internal", args, kwargs)


def internal_notify(*args, decoder=None, **kwargs):
    if decoder:
        decoder(args)
    print(args, kwargs)


@save_to_outbox
def notify(*args, **kwargs):
    internal_notify(*args, **kwargs)


@save_to_outbox_stream(EXAMPLE_STREAM)
def notify_to_stream(*args, **kwargs):
    internal_notify(*args, **kwargs)


@save_to_outbox_stream(EXAMPLE_STREAM, PublishStrategyType.KEEP_ORDER)
def notify_to_stream_overwriting_strategy(*args, **kwargs):
    internal_notify(*args, **kwargs)


@save_to_outbox_stream(EXAMPLE_STREAM, PublishStrategyType.KEEP_ORDER)
def notify_functional_to_stream_overwriting_strategy(*args, **kwargs):
    with open(kwargs["filepath"], "w") as write_file:
        json.dump(args, write_file, indent=4)


def notify_without_decorator(*args, **kwargs):
    internal_notify(*args, **kwargs)


__all__ = ("notify", "notify_without_decorator")
