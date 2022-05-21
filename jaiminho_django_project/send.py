from jaiminho.send import save_to_outbox


def internal_send(type, action, payload):
    print(type, action, payload)


@save_to_outbox
def send(type, action, payload):
    internal_send(type, action, payload)
