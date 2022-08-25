from datetime import datetime
from unittest import mock
from unittest.mock import call

import dill
import pytest
from dateutil.tz import UTC
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from freezegun import freeze_time

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
from jaiminho.tests.factories import EventFactory
from jaiminho_django_project.management.commands import validate_events_relay
from jaiminho_django_project.send import notify, notify_without_decorator

pytestmark = pytest.mark.django_db


class TestValidateEventsRelay:
    @pytest.fixture
    def mock_log_metric(self, mocker):
        return mocker.patch("jaiminho_django_project.app.signals.log_metric")

    @pytest.fixture
    def mock_capture_exception(self, mocker):
        return mocker.patch(
            "jaiminho_django_project.management.commands.validate_events_relay.Command.capture_message_fn"
        )

    @pytest.fixture
    def mock_event_published_signal(self, mocker):
        return mocker.patch("jaiminho.publish_strategies.event_published.send")

    @pytest.fixture
    def mock_event_failed_to_publish_signal(self, mocker):
        return mocker.patch("jaiminho.publish_strategies.event_failed_to_publish.send")

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
        mock.side_effect = Exception("Some error")
        return mock

    @pytest.fixture
    def failed_event(self):
        return EventFactory(
            function=dill.dumps(notify),
        )

    @pytest.fixture
    def successful_event(self):
        return EventFactory(
            function=dill.dumps(notify),
            sent_at=datetime(2022, 2, 19, tzinfo=UTC),
        )

    @pytest.fixture
    def mock_capture_exception_fn(self):
        return mock.Mock()

    @pytest.fixture
    def mock_should_delete_after_send(self, mocker):
        return mocker.patch("jaiminho.send.settings.delete_after_send", True)

    @pytest.fixture
    def mock_should_not_delete_after_send(self, mocker):
        return mocker.patch("jaiminho.send.settings.delete_after_send", False)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_relay_failed_event(
        self,
        mock_log_metric,
        failed_event,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        assert Event.objects.all().count() == 1

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(dill.loads(failed_event.message))
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_relay_failed_event_should_delete_after_send(
        self,
        mock_log_metric,
        failed_event,
        mock_internal_notify,
        mock_should_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        assert Event.objects.all().count() == 1

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(
            dill.loads(failed_event.message),
        )
        assert Event.objects.all().count() == 0

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_trigger_the_correct_signal_when_resent_successfully(
        self,
        failed_event,
        mock_log_metric,
        mock_internal_notify,
        mock_event_published_signal,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_event_published_signal.assert_not_called()
        mock_log_metric.assert_called_once_with(
            "event-published-through-outbox", dill.loads(failed_event.message)
        )

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_trigger_the_correct_signal_when_resent_failed(
        self,
        failed_event,
        mock_log_metric,
        mock_internal_notify_fail,
        mock_event_failed_to_publish_signal,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        call_command(validate_events_relay.Command())

        mock_internal_notify_fail.assert_called_once()
        mock_event_failed_to_publish_signal.assert_not_called()
        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish-through-outbox", dill.loads(failed_event.message)
        )

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_doest_not_relay_when_does_not_exist_failed_events(
        self, successful_event, caplog, publish_strategy, mocker,
    ):
        assert Event.objects.filter(sent_at__isnull=True).count() == 0
        assert Event.objects.filter(sent_at__isnull=False).count() == 1
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        call_command(validate_events_relay.Command())

        assert "No failed events found." in caplog.text
        assert Event.objects.all().count() == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_relay_every_event_even_at_lest_one_fail(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
        )

        call_command(validate_events_relay.Command())

        call_1 = call(dill.loads(event_1.message), encoder=DjangoJSONEncoder, a="1")
        call_2 = call(dill.loads(event_2.message), encoder=DjangoJSONEncoder, a="2")
        mock_internal_notify_fail.assert_has_calls([call_1, call_2], any_order=True)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.KEEP_ORDER,)
    )
    def test_relay_stuck_when_one_fail(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
        )

        call_command(validate_events_relay.Command())
        mock_internal_notify_fail.assert_called_once_with(
            dill.loads(event_2.message),
            encoder=DjangoJSONEncoder,
            a="1",
        )
        assert "Events relaying are stuck due to failing Event" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_events_ordered_by_created_by_relay(self, mock_internal_notify, publish_strategy, mocker):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        with freeze_time("2022-01-03"):
            event_1 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            )
        with freeze_time("2022-01-01"):
            event_2 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            )
        with freeze_time("2022-01-02"):
            event_3 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "3"}),
            )

        call_command(validate_events_relay.Command())

        call_1 = call(dill.loads(event_1.message), encoder=DjangoJSONEncoder, a="1")
        call_2 = call(dill.loads(event_2.message), encoder=DjangoJSONEncoder, a="2")
        call_3 = call(dill.loads(event_3.message), encoder=DjangoJSONEncoder, a="3")
        mock_internal_notify.assert_has_calls([call_2, call_3, call_1], any_order=False)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_relay_message_when_notify_function_is_not_decorated(
        self, mock_internal_notify, mock_should_not_delete_after_send, publish_strategy, mocker
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        event = EventFactory(
            function=dill.dumps(notify_without_decorator),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder}),
        )

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(
            dill.loads(event.message), encoder=DjangoJSONEncoder
        )
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_dont_create_another_event_when_relay_fails(
        self, failed_event, mock_internal_notify_fail, mock_capture_exception_fn, publish_strategy, mocker
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        mocker.patch(
            "jaiminho.send.settings.default_capture_exception",
            mock_capture_exception_fn,
        )
        assert Event.objects.all().count() == 1

        call_command(validate_events_relay.Command())

        mock_capture_exception_fn.assert_called_once()
        assert Event.objects.all().count() == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_raise_exception_when_module_does_not_exist_anymore(
        self, mocker, caplog, mock_capture_exception_fn, publish_strategy
    ):
        missing_module = b"\x80\x04\x95/\x00\x00\x00\x00\x00\x00\x00\x8c jaiminho_django_project.send_two\x94\x8c\x06notify\x94\x93\x94."
        mocker.patch(
            "jaiminho.send.settings.default_capture_exception",
            mock_capture_exception_fn,
        )
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        EventFactory(function=missing_module)

        call_command(validate_events_relay.Command())

        assert "Function does not exist anymore" in caplog.text
        assert "No module named 'jaiminho_django_project.send_two'" in caplog.text
        capture_exception_call = mock_capture_exception_fn.call_args[0][0]
        assert "No module named 'jaiminho_django_project.send_two'" == str(
            capture_exception_call
        )

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_raise_exception_when_function_does_not_exist_anymore(self, caplog, publish_strategy, mocker):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        missing_function = b"\x80\x04\x955\x00\x00\x00\x00\x00\x00\x00\x8c\x1cjaiminho_django_project.send\x94\x8c\x10missing_function\x94\x93\x94."
        EventFactory(
            function=missing_function,
        )

        call_command(validate_events_relay.Command())

        assert "Function does not exist anymore" in caplog.text
        assert "Can't get attribute 'missing_function' on" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_works_fine_without_capture_message_fn(
        self,
        mocker,
        failed_event,
        mock_internal_notify_fail,
        publish_strategy,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.default_capture_exception", None)

        call_command(validate_events_relay.Command())

        mock_internal_notify_fail.assert_called_once()

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER)
    )
    def test_works_with_custom_capture_message_fn(
        self, mocker, failed_event, mock_internal_notify_fail, publish_strategy
    ):
        mock_custom_capture_fn = mock.Mock()
        mocker.patch(
            "jaiminho.send.settings.default_capture_exception", mock_custom_capture_fn
        )
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)


        call_command(validate_events_relay.Command())

        mock_internal_notify_fail.assert_called_once()
        exception_raised = mock_custom_capture_fn.call_args[0][0]
        assert exception_raised == mock_internal_notify_fail.side_effect
        assert "Some error" == str(exception_raised)
