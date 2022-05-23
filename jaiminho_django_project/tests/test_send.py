import pytest
from jaiminho.models import Event
import jaiminho_django_project.send

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_internal_notify(mocker):
    return mocker.patch("jaiminho_django_project.send.internal_notify")


@pytest.fixture
def mock_internal_notify_fail(mocker):
    mock = mocker.patch("jaiminho_django_project.send.internal_notify")
    mock.side_effect = Exception("ups")
    return mock


@pytest.mark.parametrize(
    ("persist_all_events", "events_count"),
    (
        (False, 0),
        (True, 1),
    ),
)
def test_send_success(mock_internal_notify, mocker, persist_all_events, events_count):
    mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
    jaiminho_django_project.send.notify({"action": "a", "type": "t", "c": "d"})
    mock_internal_notify.assert_called_once_with({"action": "a", "type": "t", "c": "d"})
    assert Event.objects.all().count() == events_count


@pytest.mark.parametrize(("persist_all_events"), (False, True))
def test_send_fail(mock_internal_notify_fail, mocker, persist_all_events):
    mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
    with pytest.raises(Exception):
        jaiminho_django_project.send.notify({"action": "a", "type": "t", "c": "d"})
    mock_internal_notify_fail.assert_called_once_with(
        {"action": "a", "type": "t", "c": "d"}
    )
    assert Event.objects.all().count() == 1
    assert Event.objects.first().sent_at is None


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
    assert (
        event.options
        == "jaiminho_django_project.tests.test_send.Encoder encoder=NotUsed"
    )
