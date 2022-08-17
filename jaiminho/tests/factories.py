import factory
import uuid

from datetime import datetime
from django.core.serializers.json import DjangoJSONEncoder

from jaiminho.models import Event


class EventFactory(factory.django.DjangoModelFactory):

    message = factory.LazyAttribute(
        lambda _: b"\x80\x04\x95\n\x00\x00\x00\x00\x00\x00\x00}\x94\x8c\x01a\x94K\x01s."
    )

    class Meta:
        model = Event
