from datetime import datetime
from unittest import mock
from unittest.mock import call

import pytest
from dateutil.tz import UTC
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from freezegun import freeze_time

from jaiminho.kwargs_handler import format_kwargs
from jaiminho.management.commands.events_relay import Command
from jaiminho.models import Event
from jaiminho.tests.factories import EventFactory
from jaiminho_django_project.management.commands import validate_events_relay
from jaiminho_django_project.send import notify

pytestmark = pytest.mark.django_db


class TestValidateEventsRelay:
    @pytest.fixture
    def mock_log_info(self, mocker):
        return mocker.patch("jaiminho.management.commands.events_relay.log.info")

    @pytest.fixture
    def mock_log_warning(self, mocker):
        return mocker.patch("jaiminho.management.commands.events_relay.log.warning")

    @pytest.fixture
    def mock_capture_exception(self, mocker):
        return mocker.patch(
            "jaiminho_django_project.management.commands.validate_events_relay.Command.capture_exception_fn"
        )

    @pytest.fixture
    def mock_event_published_signal(self, mocker):
        return mocker.patch("jaiminho.send.event_published.send")

    @pytest.fixture
    def mock_event_failed_to_publish_signal(self, mocker):
        return mocker.patch(
            "jaiminho.send.event_failed_to_publish.send"
        )

    @pytest.fixture
    def mock_event_published_by_events_relay_signal(self, mocker):
        return mocker.patch(
            "jaiminho.management.commands.events_relay.event_published_by_events_relay.send"
        )

    @pytest.fixture
    def mock_event_failed_to_publish_by_events_relay_signal(self, mocker):
        return mocker.patch(
            "jaiminho.management.commands.events_relay.event_failed_to_publish_by_events_relay.send"
        )

    @pytest.fixture
    def mock_internal_notify(self, mocker):
        return mocker.patch("jaiminho_django_project.send.internal_notify")

    @pytest.fixture
    def mock_internal_notify_fail(self, mocker):
        mock = mocker.patch("jaiminho_django_project.send.internal_notify")
        mock.side_effect = Exception("ups")
        return mock

    @pytest.fixture
    def failed_event(self):
        return EventFactory(
            function_signature="jaiminho_django_project.send.notify",
            encoder="django.core.serializers.json.DjangoJSONEncoder",
        )

    @pytest.fixture
    def successful_event(self):
        return EventFactory(
            function_signature="jaiminho_django_project.send.notify",
            encoder="django.core.serializers.json.DjangoJSONEncoder",
            sent_at=datetime(2022, 2, 19, tzinfo=UTC),
        )

    @pytest.fixture
    def mock_capture_exception_fn(self):
        return mock.Mock()

    @pytest.fixture
    def command_without_capture_exception_fn(self):
        class WithoutCaptureExceptionFn(Command):
            capture_exception_fn = None

        return WithoutCaptureExceptionFn

    @pytest.fixture
    def command_with_custom_capture_exception(self, mock_capture_exception_fn):
        class WithCustomCaptureException(Command):
            capture_exception_fn = mock_capture_exception_fn

        return WithCustomCaptureException

    def test_relay_failed_event(self, failed_event, mock_internal_notify):
        assert Event.objects.all().count() == 1

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(
            failed_event.payload, encoder=DjangoJSONEncoder
        )
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    def test_trigger_the_correct_signal_when_resent_successfully(
        self,
        failed_event,
        mock_internal_notify,
        mock_event_published_signal,
        mock_event_published_by_events_relay_signal,
    ):
        call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_event_published_signal.assert_not_called()
        mock_event_published_by_events_relay_signal.assert_called_once()
        mock_args = mock_event_published_by_events_relay_signal.call_args_list[0].kwargs
        if "sender" in mock_args:
            assert mock_args["sender"].__name__ == "notify"
            assert mock_args["instance"] == failed_event.payload
        else:
            assert mock_args[0] == "notify"
            assert mock_args[1] == failed_event.payload

    def test_trigger_the_correct_signal_when_resent_failed(
        self,
        failed_event,
        mock_internal_notify_fail,
        mock_event_failed_to_publish_signal,
        mock_event_failed_to_publish_by_events_relay_signal,
    ):
        call_command(validate_events_relay.Command())

        mock_internal_notify_fail.assert_called_once()
        mock_event_failed_to_publish_signal.assert_not_called()
        mock_event_failed_to_publish_by_events_relay_signal.assert_called_once()
        mock_args = mock_event_failed_to_publish_by_events_relay_signal.call_args_list[0].kwargs
        if "sender" in mock_args:
            assert mock_args["sender"].__name__ == "notify"
            assert mock_args["instance"] == failed_event.payload
        else:
            assert mock_args[0] == "notify"
            assert mock_args[1] == failed_event.payload

    def test_doest_not_relay_when_does_not_exist_failed_events(
        self, successful_event, mock_log_info
    ):
        assert Event.objects.filter(sent_at__isnull=True).count() == 0
        assert Event.objects.filter(sent_at__isnull=False).count() == 1

        call_command(validate_events_relay.Command())

        mock_log_info.assert_called_with("No failed events found.")
        assert Event.objects.all().count() == 1

    def test_relay_every_event_even_at_lest_one_fail(
        self,
        mock_internal_notify_fail,
    ):
        function_signature = "jaiminho_django_project.send.notify"
        encoder = "django.core.serializers.json.DjangoJSONEncoder"
        event_1 = EventFactory(
            function_signature=function_signature,
            encoder=encoder,
            options=format_kwargs(a="1"),
        )
        event_2 = EventFactory(
            function_signature=function_signature,
            encoder=encoder,
            options=format_kwargs(a="2"),
        )

        call_command(validate_events_relay.Command())

        call_1 = call(event_1.payload, encoder=DjangoJSONEncoder, a="1")
        call_2 = call(event_2.payload, encoder=DjangoJSONEncoder, a="2")
        mock_internal_notify_fail.assert_has_calls([call_1, call_2], any_order=True)

    def test_events_ordered_by_created_by_relay(self, mock_internal_notify):
        function_signature = "jaiminho_django_project.send.notify"
        encoder = "django.core.serializers.json.DjangoJSONEncoder"
        with freeze_time("2022-01-03"):
            event_1 = EventFactory(
                function_signature=function_signature,
                encoder=encoder,
                options=format_kwargs(a="1"),
            )
        with freeze_time("2022-01-01"):
            event_2 = EventFactory(
                function_signature=function_signature,
                encoder=encoder,
                options=format_kwargs(a="2"),
            )
        with freeze_time("2022-01-02"):
            event_3 = EventFactory(
                function_signature=function_signature,
                encoder=encoder,
                options=format_kwargs(a="3"),
            )

        call_command(validate_events_relay.Command())

        call_1 = call(event_1.payload, encoder=DjangoJSONEncoder, a="1")
        call_2 = call(event_2.payload, encoder=DjangoJSONEncoder, a="2")
        call_3 = call(event_3.payload, encoder=DjangoJSONEncoder, a="3")
        mock_internal_notify.assert_has_calls([call_2, call_3, call_1], any_order=False)

    def test_relay_message_when_notify_function_is_not_decorated(
        self, mock_internal_notify
    ):
        event = EventFactory(
            function_signature="jaiminho_django_project.send.notify_without_decorator",
            encoder="django.core.serializers.json.DjangoJSONEncoder",
        )

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(
            event.payload, encoder=DjangoJSONEncoder
        )
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    def test_dont_create_another_event_when_relay_fails(
        self, failed_event, mock_internal_notify_fail, mock_capture_exception
    ):
        assert Event.objects.all().count() == 1

        call_command(validate_events_relay.Command())

        mock_capture_exception.assert_called_once()
        assert Event.objects.all().count() == 1

    def test_raise_exception_when_module_does_not_exist_anymore(self, mock_log_warning):
        EventFactory(
            function_signature="jaiminho_django_project.missing_module.notify",
            encoder="django.core.serializers.json.DjangoJSONEncoder",
        )

        call_command(validate_events_relay.Command())

        mock_log_warning.assert_called_once()
        mock_calls = mock_log_warning.call_args[0]
        assert "Function does not exist anymore" in mock_calls[0]
        assert (
            "No module named 'jaiminho_django_project.missing_module'" in mock_calls[1]
        )

    def test_raise_exception_when_function_does_not_exist_anymore(
        self, mock_log_warning
    ):
        EventFactory(
            function_signature="jaiminho_django_project.send.missing_notify",
            encoder="django.core.serializers.json.DjangoJSONEncoder",
        )

        call_command(validate_events_relay.Command())

        mock_log_warning.assert_called_once()
        mock_calls = mock_log_warning.call_args[0]
        assert "Function does not exist anymore" in mock_calls[0]
        assert (
            "'jaiminho_django_project.send' has no attribute 'missing_notify'"
            in mock_calls[1]
        )

    def test_works_fine_without_capture_exception_fn(
        self,
        failed_event,
        command_without_capture_exception_fn,
        mock_internal_notify_fail,
    ):
        call_command(command_without_capture_exception_fn())

        mock_internal_notify_fail.assert_called_once()

    def test_works_with_custom_capture_exception_fn(
        self,
        failed_event,
        mock_capture_exception_fn,
        command_with_custom_capture_exception,
        mock_internal_notify_fail,
    ):
        call_command(command_with_custom_capture_exception())

        mock_internal_notify_fail.assert_called_once()
        mock_capture_exception_fn.assert_called_once()
