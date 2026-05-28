from datetime import datetime

import pytest
from dateutil.tz import UTC
from freezegun import freeze_time

from django.core.signing import BadSignature
from jaiminho.tests.factories import EventFactory
from jaiminho.models import Event


@pytest.mark.django_db
class TestEvent:
    @pytest.fixture(autouse=True)
    def mock_settings(self, mocker):
        mocker.patch("jaiminho.settings.verify_events_signature", True)
        mocker.patch("jaiminho.settings.sign_events", True)

    def test_mark_as_sent(self):
        event = EventFactory()
        assert event.sent_at is None

        with freeze_time("2022-01-01"):
            event.mark_as_sent()
            assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)

    @pytest.mark.parametrize(
        "payload,expected_signature",
        [
            ({"message": b"message"}, "ME8-7L8XjJPI7rs5w1pJtnpolu31c6vQ-EzlXwCBIdc"),
            ({"kwargs": b"kwargs"}, "lVLH-Uup6DUH8zILRnZ9bReV-XZpJf73pqDsacI6w40"),
            ({"function": b"function"}, "MdN3qNL9b2sZnruiJAvRRrtaC9ZCojJ6yP3_nx-tvdQ"),
            (
                {"message": b"message", "kwargs": b"kwargs"},
                "nG77dEJNI5I7ScNS4caN53j9nMl46Y74gwYo2mHAk8Y",
            ),
            (
                {"kwargs": b"message", "function": b"kwargs"},
                "XskQA6Sf4K8gWh1crsLilRgpquWgzSpD1jDszuZ4C68",
            ),
            (
                {"function": b"function", "message": b"message"},
                "T7BuzgdqnGvyAx726eqob8P-skuaaqDJixfy9eZf9E0",
            ),
            (
                {"message": b"message", "kwargs": b"kwargs", "function": b"function"},
                "sJTwMGYVU-Dd5IBQcBkLzmNUQONTelR8uoO5gXqP9XM",
            ),
        ],
    )
    def test_generates_functioning_signature_on_save(self, payload, expected_signature):
        initial_payload = {"message": None, "kwargs": None, "function": None}

        initial_payload.update(payload)

        event = EventFactory.create(**initial_payload)

        event.save()
        event.refresh_from_db()

        try:
            event.verify_integrity()
        except BadSignature:
            pytest.fail("Verify integrity should not raise BadSignature")

        assert event.signature == expected_signature

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
    def test_verify_integrity_of_events_without_signature(self, field, value):
        payload = {"message": None, "kwargs": None, "function": None}

        payload.update({field: value})

        event = EventFactory.create(**payload)

        Event.objects.update(signature=None)
        event.refresh_from_db()

        with pytest.raises(BadSignature):
            event.verify_integrity()

    def test_verify_integrity_of_events_without_signature_and_values_does_not_raise(
        self,
    ):
        payload = {"message": None, "kwargs": None, "function": None}

        event = EventFactory.create(**payload)

        try:
            event.verify_integrity()
        except BadSignature:
            pytest.fail("Verify integrity should not raise BadSignature")

    def test_verify_integrity_does_nothing_when_disabled_through_settings(self, mocker):
        mocker.patch("jaiminho.settings.verify_events_signature", False)
        event = EventFactory.create(message=b"message")

        Event.objects.update(**{"message": b"tampered-value"})
        event.refresh_from_db()

        try:
            event.verify_integrity()
        except BadSignature:
            pytest.fail("Verify integrity should not raise BadSignature")

    def test_signature_is_not_generated_when_disabled_through_settings(self, mocker):
        mocker.patch("jaiminho.settings.sign_events", False)
        event = EventFactory.create(message=b"message")

        assert event.signature is None
