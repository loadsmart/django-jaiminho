import pytest
from jaiminho.models import Event
import jaiminho_django_project.send

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_internal_send(mocker):
    return mocker.patch("jaiminho_django_project.send.internal_send")


@pytest.fixture
def mock_internal_send_fail(mocker):
    mock = mocker.patch("jaiminho_django_project.send.internal_send")
    mock.side_effect = Exception("ups")
    return mock


@pytest.mark.parametrize(
    ('persist_all_events', 'events_count'),
    (
            (False, 0),
            (True, 1),
    )
)
def test_send_success(mock_internal_send, mocker, persist_all_events, events_count):
    mocker.patch('jaiminho.send.settings.persist_all_events', persist_all_events)
    jaiminho_django_project.send.send("a", "b", {"c": "d"})
    mock_internal_send.assert_called_once_with("a", "b", {"c": "d"})
    assert Event.objects.all().count() == events_count



@pytest.mark.parametrize(
    ('persist_all_events'),
    ( False, True)
)
def test_send_fail(mock_internal_send_fail, mocker, persist_all_events):
    mocker.patch('jaiminho.send.settings.persist_all_events', persist_all_events)
    with pytest.raises(Exception):
        jaiminho_django_project.send.send("a", "b", {"c": "d"})
    mock_internal_send_fail.assert_called_once_with("a", "b", {"c": "d"})
    assert Event.objects.all().count() == 1
    assert Event.objects.first().sent_at is None
