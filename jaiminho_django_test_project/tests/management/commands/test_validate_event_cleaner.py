import pytest

from datetime import timedelta
from django.core.management import call_command
from django.utils import timezone

from jaiminho.models import Event
from jaiminho.tests.factories import EventFactory
from jaiminho_django_test_project.management.commands import validate_event_cleaner

pytestmark = pytest.mark.django_db


class TestEventCleanerCommand:
    TIME_TO_DELETE = timedelta(days=5)

    @pytest.fixture
    def older_events(self):
        return EventFactory.create_batch(
            2, sent_at=timezone.now() - self.TIME_TO_DELETE - timedelta(days=1)
        )

    @pytest.fixture
    def newer_events(self):
        return EventFactory.create_batch(
            2, sent_at=timezone.now() - self.TIME_TO_DELETE + timedelta(days=1)
        )

    @pytest.fixture
    def not_sent_events(self):
        return EventFactory.create_batch(2, sent_at=None)

    @pytest.fixture
    def events_older_than_default_config(self):
        return EventFactory.create_batch(
            2, sent_at=timezone.now() - self.TIME_TO_DELETE - timedelta(days=30)
        )

    def test_command_with_misconfigured_time_to_delete_raises_error_and_doesnt_delete(
        self, mocker, older_events, newer_events, not_sent_events
    ):
        mocker.patch("jaiminho.send.settings.time_to_delete", "not-a-timedelta")

        assert len(Event.objects.all()) == 6

        with pytest.raises(AssertionError):
            call_command(validate_event_cleaner.Command())

        assert len(Event.objects.all()) == 6

    def test_command_deletes_older_events(
        self, mocker, older_events, newer_events, not_sent_events, caplog
    ):
        mocker.patch("jaiminho.send.settings.time_to_delete", self.TIME_TO_DELETE)

        assert len(Event.objects.all()) == 6
        call_command(validate_event_cleaner.Command())

        remaining_events = Event.objects.all()
        assert len(remaining_events) == 4
        assert set(remaining_events) == set([*newer_events, *not_sent_events])
        assert "JAIMINHO-EVENT-CLEANER: Successfully deleted" in caplog.text

    def test_command_doesnt_delete_when_there_are_no_older_events(
        self, mocker, newer_events, not_sent_events, caplog
    ):
        mocker.patch("jaiminho.send.settings.time_to_delete", self.TIME_TO_DELETE)

        assert len(Event.objects.all()) == 4
        call_command(validate_event_cleaner.Command())
        assert len(Event.objects.all()) == 4

    def test_command_without_time_to_delete_configuration_uses_default_7_days(
        self,
        older_events,
        newer_events,
        not_sent_events,
        events_older_than_default_config,
    ):
        assert len(Event.objects.all()) == 8
        call_command(validate_event_cleaner.Command())

        remaining_events = Event.objects.all()
        assert set(remaining_events) == set(
            [*older_events, *newer_events, *not_sent_events]
        )
        assert len(Event.objects.all()) == 6
