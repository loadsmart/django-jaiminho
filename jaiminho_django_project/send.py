from jaiminho.constants import PublishStrategyType
from jaiminho.send import save_to_outbox, save_to_outbox_stream


EXAMPLE_STREAM = "my-stream"


class InternalDecoder:
    def __call__(self, *args, **kwargs):
        print("Hello Internal", args, kwargs)


def internal_notify(payload, decoder=None, **kwargs):
    if decoder:
        decoder(payload)
    print(payload, kwargs)


@save_to_outbox
def notify(payload, **kwargs):
    internal_notify(payload, **kwargs)


@save_to_outbox_stream(EXAMPLE_STREAM)
def notify_to_stream(payload, **kwargs):
    internal_notify(payload, **kwargs)


@save_to_outbox_stream(EXAMPLE_STREAM, PublishStrategyType.KEEP_ORDER)
def notify_to_stream_overwriting_strategy(payload, **kwargs):
    internal_notify(payload, **kwargs)


def notify_without_decorator(payload, **kwargs):
    internal_notify(payload, **kwargs)


__all__ = ("notify", "notify_without_decorator")
