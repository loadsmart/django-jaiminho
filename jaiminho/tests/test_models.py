from datetime import datetime

import pytest
from dateutil.tz import UTC
from freezegun import freeze_time

from django.core.signing import BadSignature
from jaiminho.tests.factories import EventFactory
from jaiminho.models import Event


@pytest.mark.django_db
class TestEvent:
    def test_mark_as_sent(self):
        event = EventFactory()
        assert event.sent_at is None

        with freeze_time("2022-01-01"):
            event.mark_as_sent()
            assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)

    @pytest.mark.parametrize(
        "field,value,expected_key",
        [
            ("message", b"message", "ME8-7L8XjJPI7rs5w1pJtnpolu31c6vQ-EzlXwCBIdc"),
            ("kwargs", b"kwargs", "lVLH-Uup6DUH8zILRnZ9bReV-XZpJf73pqDsacI6w40"),
            ("function", b"function", "MdN3qNL9b2sZnruiJAvRRrtaC9ZCojJ6yP3_nx-tvdQ"),
            ("message", None, None),
            ("kwargs", None, None),
            ("function", None, None),
        ],
    )
    def test_generates_signing_keys_on_save(self, field, value, expected_key):
        event = EventFactory.create()

        setattr(event, field, value)
        event.save()
        event.refresh_from_db()

        assert getattr(event, f"{field}_signing_key") == expected_key

    @pytest.mark.parametrize(
        "field,value",
        [
            ("message", b"message"),
            ("kwargs", b"kwargs"),
            ("function", b"function"),
            ("message", None),
            ("kwargs", None),
            ("function", None),
        ],
    )
    def test_verify_integrity_of_untampered_event(self, field, value):
        event = EventFactory.create()

        setattr(event, field, value)
        event.save()
        event.refresh_from_db()

        event.verify_integrity()

    @pytest.mark.parametrize(
        "field",
        [
            "message",
            "kwargs",
            "function",
        ],
    )
    def test_verify_integrity_of_tampered_event(self, field):

        event = EventFactory.create(
            message=b"message", kwargs=b"kwargs", function=b"function"
        )

        Event.objects.update(**{field: b"tampered-value"})
        event.refresh_from_db()

        with pytest.raises(BadSignature):
            event.verify_integrity()

    @pytest.mark.parametrize(
        "field,value",
        [
            ("message", b"message"),
            ("kwargs", b"kwargs"),
            ("function", b"function"),
        ],
    )
    def test_verify_integrity_of_events_without_keys(self, field, value):
        payload = {"message": None, "kwargs": None, "function": None}

        payload.update({field: value})

        event = EventFactory.create(**payload)

        Event.objects.update(
            message_signing_key=None, kwargs_signing_key=None, function_signing_key=None
        )
        event.refresh_from_db()

        with pytest.raises(BadSignature):
            event.verify_integrity()

    @pytest.mark.parametrize(
        "field,value",
        [
            ("message", None),
            ("kwargs", None),
            ("function", None),
        ],
    )
    def test_verify_integrity_of_events_without_keys_and_values_should_not_raise(self, field, value):
        payload = {"message": b"message", "kwargs": b"kwargs", "function": b"function"}

        payload.update({field: value})

        event = EventFactory.create(**payload)

        Event.objects.update(**{f"{field}_signing_key": None})
        event.refresh_from_db()
        try:
            event.verify_integrity()
        except BadSignature:
            pytest.fail("Verify integrity should not raise BadSignature")
