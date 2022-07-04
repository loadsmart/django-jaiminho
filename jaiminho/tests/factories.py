import factory
import uuid

from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

from jaiminho.models import Event


class EventFactory(factory.django.DjangoModelFactory):

    type = "generic_event"
    action = "created"
    payload = factory.LazyAttribute(
        lambda _: {
            "generic_object": {"uuid": str(uuid.uuid4())},
            "action": "created",
        }
    )

    class Meta:
        model = Event