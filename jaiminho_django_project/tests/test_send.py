from datetime import datetime

import pytest
from dateutil.tz import UTC
from django.core.serializers.json import DjangoJSONEncoder
from freezegun import freeze_time

from jaiminho.models import Event
import jaiminho_django_project.send

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_log_metric(mocker):
    return mocker.patch("jaiminho_django_project.app.signals.log_metric")


@pytest.fixture
def mock_internal_notify(mocker):
    return mocker.patch("jaiminho_django_project.send.internal_notify")


@pytest.fixture
def mock_internal_notify_fail(mocker):
    mock = mocker.patch("jaiminho_django_project.send.internal_notify")
    mock.side_effect = Exception("ups")
    return mock


@pytest.fixture
def mock_event_published_signal(mocker):
    return mocker.patch("jaiminho.send.event_published.send")


@pytest.fixture
def mock_event_failed_to_publish_signal(mocker):
    return mocker.patch("jaiminho.send.event_failed_to_publish.send")


@pytest.mark.parametrize(
    ("persist_all_events", "events_count"),
    (
        (False, 0),
        (True, 1),
    ),
)
def test_send_success(
    mock_internal_notify, mock_log_metric, mocker, persist_all_events, events_count
):
    mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
    payload = {"action": "a", "type": "t", "c": "d"}
    jaiminho_django_project.send.notify(payload)
    mock_internal_notify.assert_called_once_with(payload, encoder=DjangoJSONEncoder)
    assert Event.objects.all().count() == events_count
    mock_log_metric.assert_called_once_with("event-published", payload)


def test_send_success_with_encoder(mock_log_metric, mock_internal_notify, mocker):
    mocker.patch("jaiminho.send.settings.persist_all_events", True)
    payload = {"action": "a", "type": "t", "c": "d"}

    with freeze_time("2022-01-01"):
        jaiminho_django_project.send.notify(payload)

    mock_internal_notify.assert_called_once_with(payload, encoder=DjangoJSONEncoder)
    assert Event.objects.all().count() == 1
    event = Event.objects.first()
    assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)
    assert event.options == ""
    assert event.encoder == "django.core.serializers.json.DjangoJSONEncoder"
    assert event.function_signature == "jaiminho_django_project.send.notify"
    mock_log_metric.assert_called_once_with("event-published", payload)


@pytest.mark.parametrize(("persist_all_events"), (False, True))
def test_send_fail(
    mock_log_metric, mock_internal_notify_fail, mocker, persist_all_events
):
    mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
    payload = {"action": "a", "type": "t", "c": "d"}
    with pytest.raises(Exception):
        jaiminho_django_project.send.notify(payload)
    mock_internal_notify_fail.assert_called_once_with(
        payload, encoder=DjangoJSONEncoder
    )
    assert Event.objects.all().count() == 1
    assert Event.objects.first().sent_at is None
    mock_log_metric.assert_called_once_with("event-failed-to-publish", payload)


def test_send_trigger_event_published_signal(
    mock_internal_notify, mock_event_published_signal
):
    jaiminho_django_project.send.notify({"action": "a", "type": "t", "c": "d"})
    mock_event_published_signal.assert_called_once()


def test_send_trigger_event_failed_to_publish_signal(
    mock_internal_notify_fail, mock_event_failed_to_publish_signal
):
    with pytest.raises(Exception):
        jaiminho_django_project.send.notify({"action": "a", "type": "t", "c": "d"})
        mock_event_failed_to_publish_signal.assert_called_once()


# we need this in the globals so we don't need to mock A LOT of things
class Encoder:
    pass


@pytest.fixture
def encoder():
    return Encoder


def test_send_with_parameters(mock_internal_notify_fail, encoder):
    with pytest.raises(Exception):
        jaiminho_django_project.send.notify(
            {"action": "a", "type": "t", "c": "d"}, encoder=encoder
        )
    assert Event.objects.all().count() == 1
    event = Event.objects.first()
    assert event.sent_at is None
    assert event.options == ""
    assert event.encoder == "jaiminho_django_project.tests.test_send.Encoder"
    assert event.function_signature == "jaiminho_django_project.send.notify"


def test_send_fail_with_encoder_default(mock_internal_notify_fail):
    payload = {"action": "a", "type": "t", "c": "d"}

    with pytest.raises(Exception):
        jaiminho_django_project.send.notify(payload)

    mock_internal_notify_fail.assert_called_with(payload, encoder=DjangoJSONEncoder)
    assert Event.objects.all().count() == 1
    event = Event.objects.first()
    assert event.sent_at is None
    assert event.options == ""
    assert event.encoder == "django.core.serializers.json.DjangoJSONEncoder"
    assert event.function_signature == "jaiminho_django_project.send.notify"
