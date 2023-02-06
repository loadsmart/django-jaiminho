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
from jaiminho.relayer import EventRelayer
from jaiminho.tests.factories import EventFactory
from jaiminho_django_test_project.management.commands import validate_events_relay
from jaiminho_django_test_project.send import (
    notify,
    notify_without_decorator,
    notify_to_stream,
)

pytestmark = pytest.mark.django_db


class TestValidateEventsRelay:
    @pytest.fixture
    def mock_log_metric(self, mocker):
        return mocker.patch("jaiminho_django_test_project.app.signals.log_metric")

    @pytest.fixture
    def mock_capture_exception(self, mocker):
        return mocker.patch(
            "jaiminho_django_test_project.management.commands.validate_events_relay.Command.capture_message_fn"
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
        return mocker.patch("jaiminho_django_test_project.send.internal_notify")

    @pytest.fixture
    def mock_internal_notify_fail(self, mocker):
        mock = mocker.patch("jaiminho_django_test_project.send.internal_notify")
        mock.side_effect = Exception("Some error")
        return mock

    @pytest.fixture
    def failed_event(self):
        return EventFactory(
            function=dill.dumps(notify), message=dill.dumps(({"b": 1},))
        )

    @pytest.fixture
    def failed_event_with_kwargs(self):
        return EventFactory(
            function=dill.dumps(notify), kwargs=dill.dumps({"ab": 2, "ac": 3})
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
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
        mock_internal_notify.assert_called_with(*dill.loads(failed_event.message))
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_relay_failed_event_when_message_is_not_a_tuple(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        payload = {"b": 1}
        failed_event = EventFactory(
            function=dill.dumps(notify),
            message=dill.dumps(payload),
        )

        assert Event.objects.all().count() == 1

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event == failed_event
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)
        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(payload)

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_relay_failed_event_from_empty_stream(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        first_event = EventFactory(
            function=dill.dumps(notify),
            message=dill.dumps(({"b": 1},)),
        )
        second_event = EventFactory(
            function=dill.dumps(notify_to_stream),
            stream="my-stream",
            message=dill.dumps(({"b": 2},)),
        )
        third_event = EventFactory(
            function=dill.dumps(notify_to_stream),
            stream="my-other-stream",
            message=dill.dumps(({"b": 3},)),
        )
        assert Event.objects.all().count() == 3

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once_with(*dill.loads(first_event.message))

        assert Event.objects.all().count() == 3
        assert Event.objects.get(id=first_event.id).sent_at == datetime(
            2022, 10, 31, tzinfo=UTC
        )
        assert Event.objects.get(id=second_event.id).sent_at is None
        assert Event.objects.get(id=third_event.id).sent_at is None

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_relay_failed_event_from_specific_stream(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        first_event = EventFactory(
            function=dill.dumps(notify),
            message=dill.dumps(({"b": 1},)),
        )
        second_event = EventFactory(
            function=dill.dumps(notify_to_stream),
            stream="my-stream",
            message=dill.dumps(({"b": 2},)),
        )
        third_event = EventFactory(
            function=dill.dumps(notify_to_stream),
            stream="my-other-stream",
            message=dill.dumps(({"b": 3},)),
        )
        assert Event.objects.all().count() == 3

        with freeze_time("2022-10-31"):
            call_command(
                validate_events_relay.Command(),
                stream="my-stream",
            )

        mock_internal_notify.assert_called_once_with(*dill.loads(second_event.message))

        assert Event.objects.all().count() == 3
        assert Event.objects.get(id=first_event.id).sent_at is None
        assert Event.objects.get(id=second_event.id).sent_at == datetime(
            2022, 10, 31, tzinfo=UTC
        )
        assert Event.objects.get(id=third_event.id).sent_at is None

    def test_relay_must_loop_when_run_in_loop_using_kwargs(
        self,
        mock_log_metric,
        mocker,
    ):
        event_relayer_mock = mocker.MagicMock(spec=EventRelayer)
        event_relayer_mock.relay.side_effect = [None, None, Exception()]

        with pytest.raises(Exception):
            command = validate_events_relay.Command()
            command.event_relayer = event_relayer_mock
            call_command(command, run_in_loop=True, loop_interval=0.1)

        assert event_relayer_mock.relay.call_count == 3

    def test_relay_must_loop_when_run_using_param(
        self,
        mock_log_metric,
        mocker,
    ):
        event_relayer_mock = mocker.MagicMock(spec=EventRelayer)
        event_relayer_mock.relay.side_effect = [None, None, Exception()]

        with pytest.raises(Exception):
            command = validate_events_relay.Command()
            command.event_relayer = event_relayer_mock
            call_command(command, "--run-in-loop", "--loop-interval", 0.1)

        assert event_relayer_mock.relay.call_count == 3

    def test_does_not_run_in_loop_by_default(
        self,
        mock_log_metric,
        mocker,
    ):
        event_relayer_mock = mocker.MagicMock(spec=EventRelayer)
        event_relayer_mock.relay.side_effect = [None, None, Exception()]

        command = validate_events_relay.Command()
        command.event_relayer = event_relayer_mock
        call_command(command)

        assert event_relayer_mock.relay.call_count == 1

    def test_does_not_run_in_loop_when_receiving_false_as_kwargs(
        self,
        mock_log_metric,
        mocker,
    ):
        event_relayer_mock = mocker.MagicMock(spec=EventRelayer)
        event_relayer_mock.relay.side_effect = [None, None, Exception()]

        command = validate_events_relay.Command()
        command.event_relayer = event_relayer_mock
        call_command(command, run_in_loop=False)

        assert event_relayer_mock.relay.call_count == 1

    def test_arguments_are_optionals_when_passing_the_stream_arg(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        mocker,
    ):
        mocker.patch(
            "jaiminho.settings.publish_strategy", PublishStrategyType.PUBLISH_ON_COMMIT
        )
        args = ({"b": 1},)
        event = EventFactory(
            function=dill.dumps(notify_to_stream),
            stream="my-stream",
            message=dill.dumps(args),
        )

        with freeze_time("2022-10-31"):
            call_command(
                validate_events_relay.Command(),
                "--stream",
                "my-stream",
            )

        mock_internal_notify.assert_called_once_with(*dill.loads(event.message))

        assert Event.objects.all().count() == 1
        assert Event.objects.get(id=event.id).sent_at == datetime(
            2022, 10, 31, tzinfo=UTC
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
            *dill.loads(failed_event.message),
        )
        assert Event.objects.all().count() == 0

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
        expected_args = dill.loads(failed_event.message)
        mock_log_metric.assert_called_once_with(
            "event-published-through-outbox",
            expected_args[0],
            args=expected_args,
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_trigger_the_correct_signal_when_resent_successfully_with_kwargs(
        self,
        failed_event_with_kwargs,
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
        expected_args = dill.loads(failed_event_with_kwargs.message)
        mock_log_metric.assert_called_once_with(
            "event-published-through-outbox",
            expected_args[0],
            args=expected_args,
            **dill.loads(failed_event_with_kwargs.kwargs),
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
        expected_args = dill.loads(failed_event.message)
        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish-through-outbox",
            expected_args[0],
            args=expected_args,
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_trigger_the_correct_signal_when_resent_failed_with_kwargs(
        self,
        failed_event_with_kwargs,
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
        expected_args = dill.loads(failed_event_with_kwargs.message)
        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish-through-outbox",
            expected_args[0],
            args=expected_args,
            **dill.loads(failed_event_with_kwargs.kwargs),
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_doest_not_relay_when_does_not_exist_failed_events(
        self,
        successful_event,
        caplog,
        publish_strategy,
        mocker,
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
        args1 = ({"b": 1},)
        args2 = ({"b": 2},)
        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            message=dill.dumps(args1),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            message=dill.dumps(args2),
        )

        call_command(validate_events_relay.Command())

        call_1 = call(args1[0], encoder=DjangoJSONEncoder, a="1")
        call_2 = call(args2[0], encoder=DjangoJSONEncoder, a="2")
        mock_internal_notify_fail.assert_has_calls([call_1, call_2], any_order=True)

    @pytest.mark.parametrize("publish_strategy", (PublishStrategyType.KEEP_ORDER,))
    def test_relay_stuck_when_one_fail(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        args1 = ({"b": 1},)
        args2 = ({"b": 2},)
        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            strategy=publish_strategy,
            message=dill.dumps(args1),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            strategy=publish_strategy,
            message=dill.dumps(args2),
        )

        call_command(validate_events_relay.Command())
        mock_internal_notify_fail.assert_called_once_with(
            args1[0],
            encoder=DjangoJSONEncoder,
            a="1",
        )
        assert "Events relaying are stuck due to failing Event" in caplog.text

    @pytest.mark.parametrize("publish_strategy", (PublishStrategyType.KEEP_ORDER,))
    def test_relay_stuck_when_one_fail_and_no_strategy_on_event(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        args1 = ({"b": 1},)
        args2 = ({"b": 2},)
        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            message=dill.dumps(args1),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            message=dill.dumps(args2),
        )

        call_command(validate_events_relay.Command())
        mock_internal_notify_fail.assert_called_once_with(
            args1[0],
            encoder=DjangoJSONEncoder,
            a="1",
        )
        assert "Events relaying are stuck due to failing Event" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_relay_not_stuck_when_one_fail_and_no_strategy_on_event(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        args1 = ({"b": 1},)
        args2 = ({"b": 2},)
        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            message=dill.dumps(args1),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            message=dill.dumps(args2),
        )

        call_command(validate_events_relay.Command())
        call_1 = call(args1[0], encoder=DjangoJSONEncoder, a="1")
        call_2 = call(args2[0], encoder=DjangoJSONEncoder, a="2")
        mock_internal_notify_fail.assert_has_calls([call_1, call_2], any_order=True)
        assert "Events relaying are stuck due to failing Event" not in caplog.text

    @pytest.mark.parametrize("publish_strategy", (PublishStrategyType.KEEP_ORDER,))
    def test_relay_stuck_when_one_fail_and_specific_stream(
        self,
        mock_internal_notify_fail,
        publish_strategy,
        mocker,
        caplog,
    ):
        args1 = ({"b": 1},)
        args2 = ({"b": 2},)
        event_1 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
            strategy=publish_strategy,
            stream="my-stream",
            message=dill.dumps(args1),
        )
        event_2 = EventFactory(
            function=dill.dumps(notify),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
            strategy=publish_strategy,
            stream="my-stream",
            message=dill.dumps(args2),
        )

        call_command(
            validate_events_relay.Command(),
            stream="my-stream",
        )
        mock_internal_notify_fail.assert_called_once_with(
            args1[0],
            encoder=DjangoJSONEncoder,
            a="1",
        )
        assert "Events relaying are stuck due to failing Event" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_events_ordered_by_created_by_relay(
        self, mock_internal_notify, publish_strategy, mocker
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        message1 = ({"b": 1},)
        message2 = ({"b": 2},)
        message3 = ({"b": 3},)

        with freeze_time("2022-01-03"):
            event_1 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "1"}),
                message=dill.dumps(message1),
            )
        with freeze_time("2022-01-01"):
            event_2 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "2"}),
                message=dill.dumps(message2),
            )
        with freeze_time("2022-01-02"):
            event_3 = EventFactory(
                function=dill.dumps(notify),
                kwargs=dill.dumps({"encoder": DjangoJSONEncoder, "a": "3"}),
                message=dill.dumps(message3),
            )

        call_command(validate_events_relay.Command())

        call_1 = call(message1[0], encoder=DjangoJSONEncoder, a="1")
        call_2 = call(message2[0], encoder=DjangoJSONEncoder, a="2")
        call_3 = call(message3[0], encoder=DjangoJSONEncoder, a="3")
        mock_internal_notify.assert_has_calls([call_2, call_3, call_1], any_order=False)

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_relay_message_when_notify_function_is_not_decorated(
        self,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        args = ({"a": 1},)
        event = EventFactory(
            function=dill.dumps(notify_without_decorator),
            message=dill.dumps(args),
            kwargs=dill.dumps({"encoder": DjangoJSONEncoder}),
        )

        with freeze_time("2022-10-31"):
            call_command(validate_events_relay.Command())

        mock_internal_notify.assert_called_once()
        mock_internal_notify.assert_called_with(args[0], encoder=DjangoJSONEncoder)
        assert Event.objects.all().count() == 1
        event = Event.objects.all()[0]
        assert event.sent_at == datetime(2022, 10, 31, tzinfo=UTC)

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_dont_create_another_event_when_relay_fails(
        self,
        failed_event,
        mock_internal_notify_fail,
        mock_capture_exception_fn,
        publish_strategy,
        mocker,
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
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_raise_exception_when_module_does_not_exist_anymore(
        self, mocker, caplog, mock_capture_exception_fn, publish_strategy
    ):
        missing_module = b'\x80\x04\x95.\x00\x00\x00\x00\x00\x00\x00\x8c"jaiminho_django_test_project.send2\x94\x8c\x03foo\x94\x93\x94.'

        mocker.patch(
            "jaiminho.send.settings.default_capture_exception",
            mock_capture_exception_fn,
        )
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        EventFactory(function=missing_module)

        call_command(validate_events_relay.Command())

        assert "Function does not exist anymore" in caplog.text
        assert "No module named 'jaiminho_django_test_project.send2'" in caplog.text
        capture_exception_call = mock_capture_exception_fn.call_args[0][0]
        assert "No module named 'jaiminho_django_test_project.send2'" == str(
            capture_exception_call
        )

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_raise_exception_when_function_does_not_exist_anymore(
        self, caplog, publish_strategy, mocker
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        missing_function = b"\x80\x04\x957\x00\x00\x00\x00\x00\x00\x00\x8c!jaiminho_django_test_project.send\x94\x8c\rnever_existed\x94\x93\x94."
        EventFactory(
            function=missing_function,
        )

        call_command(validate_events_relay.Command())

        assert "Function does not exist anymore" in caplog.text
        assert "Can't get attribute 'never_existed' on" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
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
