import uuid

import factory

from jaiminho.models import Event


class EventFactory(factory.django.DjangoModelFactory):
    type = "shipment"
    action = "created"
    payload = factory.LazyAttribute(
        lambda _: {
            "shipment": {"uuid": str(uuid.uuid4())},
            "action": "created",
        }
    )

    class Meta:
        model = Event
