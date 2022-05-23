from jaiminho.send import save_to_outbox


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


__all__ = ("notify",)
