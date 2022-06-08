import pytest
from django.core.management import call_command

from jaiminho.tests.factories import EventFactory
from jaiminho_django_project.core.management.commands import validate_relay_events

pytestmark = pytest.mark.django_db


class TestValidateRelayEvents:
    @pytest.fixture
    def mock_log_info(self, mocker):
        return mocker.patch("jaiminho.management.relay_messages.log.info")

    @pytest.fixture
    def mock_log_warning(self, mocker):
        return mocker.patch("jaiminho.management.relay_messages.log.warning")

    @pytest.fixture
    def failed_event(self):
        return EventFactory(function_signature="")

    def test_relay_failed_event(self, failed_event):
        event = EventFactory()

    def test_relay_events_ordered_by_created_by(self):
        pass

    def test_relay_message_when_notify_function_is_not_decorated(self):
        pass

    def test_dont_create_another_event_when_relay_fails(self):
        pass

    def test_relay_nothing_when_does_not_exist_failed_events(self):
        pass

    def test_raise_exception_when_module_does_not_exist_anymore(self):
        pass

    def test_raise_exception_when_function_does_not_exist_anymore(self):
        pass
