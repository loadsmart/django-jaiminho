from datetime import datetime

import dill
import pytest
from dateutil.tz import UTC
from django.core.serializers.json import DjangoJSONEncoder
from freezegun import freeze_time
from django.test import TestCase

from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
import jaiminho_django_test_project.send
from jaiminho.publish_strategies import KeepOrderStrategy

pytestmark = pytest.mark.django_db


@pytest.fixture
def mock_log_metric(mocker):
    return mocker.patch("jaiminho_django_test_project.app.signals.log_metric")


@pytest.fixture
def mock_internal_notify(mocker):
    return mocker.patch("jaiminho_django_test_project.send.internal_notify")


@pytest.fixture
def mock_should_delete_after_send(mocker):
    return mocker.patch("jaiminho.send.settings.delete_after_send", True)


@pytest.fixture
def mock_should_not_delete_after_send(mocker):
    return mocker.patch("jaiminho.send.settings.delete_after_send", False)


@pytest.fixture
def mock_should_persist_all_events(mocker):
    return mocker.patch("jaiminho.send.settings.persist_all_events", True)


@pytest.fixture
def mock_internal_notify_fail(mocker):
    mock = mocker.patch("jaiminho_django_test_project.send.internal_notify")
    mock.side_effect = Exception("ups")
    return mock


@pytest.fixture
def mock_event_published_signal(mocker):
    return mocker.patch("jaiminho.publish_strategies.event_published.send")


@pytest.fixture
def mock_event_failed_to_publish_signal(mocker):
    return mocker.patch("jaiminho.publish_strategies.event_failed_to_publish.send")


# we need this in the globals so we don't need to mock A LOT of things
class Encoder:
    pass


@pytest.fixture
def encoder():
    return Encoder


class TestNotify:
    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_send_success_should_persist_all_events(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify(payload)

        assert Event.objects.all().count() == 1
        assert Event.objects.first().stream is None
        assert "JAIMINHO-SAVE-TO-OUTBOX: Event created" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_send_success_should_persist_strategy(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify(payload)

        assert Event.objects.all().count() == 1
        assert Event.objects.get().strategy == publish_strategy

    @pytest.mark.parametrize("publish_strategy", (PublishStrategyType.KEEP_ORDER,))
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_send_success_should_not_send_event_when_keep_order_strategy(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        persist_all_events,
        delete_after_send,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify(payload)

        assert not mock_internal_notify.called

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_success_should_publish_event(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(*args)

        assert len(callbacks) == 1
        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 1
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_success_should_not_persist_all_events(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(*args)
        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 0
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_success_should_delete_after_send(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_persist_all_events,
        mock_should_delete_after_send,
        caplog,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(*args)
            assert Event.objects.all().count() == 1
            event = Event.objects.get()
            assert event.sent_at is None

        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 0
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)
        assert len(callbacks) == 1
        assert (
            "JAIMINHO-ON-COMMIT-HOOK: Event deleted after success send" in caplog.text
        )

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_success_when_should_not_delete_after_send(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        caplog,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}

        with freeze_time("2022-01-01"):
            with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
                jaiminho_django_test_project.send.notify(payload)
            assert len(callbacks) == 1

        assert Event.objects.all().count() == 1
        event = Event.objects.first()
        assert Event.objects.first().stream is None
        assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)
        assert "JAIMINHO-ON-COMMIT-HOOK: Event marked as sent" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_send_fail(
        self,
        mock_log_metric,
        mock_internal_notify_fail,
        persist_all_events,
        delete_after_send,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(*args)

        mock_internal_notify_fail.assert_called_once_with(*args)
        assert Event.objects.all().count() == 1
        assert Event.objects.first().sent_at is None
        assert Event.objects.first().stream is None
        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish", args[0], args=args
        )
        assert len(callbacks) == 1
        assert "JAIMINHO-ON-COMMIT-HOOK: Event failed to be published" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        "exception",
        (AssertionError, AttributeError, Exception, SystemError, SystemExit),
    )
    def test_send_fail_handles_multiple_exceptions_type(
        self,
        mock_log_metric,
        mock_internal_notify_fail,
        exception,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        mock_internal_notify_fail.side_effect = exception

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(*args)

        mock_internal_notify_fail.assert_called_once_with(*args)

        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish", args[0], args=args
        )
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_trigger_event_published_signal(
        self,
        mock_internal_notify,
        mock_event_published_signal,
        mock_should_persist_all_events,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        args = ({"action": "a", "type": "t", "c": "d"},)

        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(
                *args, first_param="1", second_param="2"
            )

        original_func = jaiminho_django_test_project.send.notify.original_func
        mock_event_published_signal.assert_called_once_with(
            sender=original_func,
            event_payload=args[0],
            args=args,
            first_param="1",
            second_param="2",
        )
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_trigger_event_failed_to_publish_signal(
        self,
        mock_internal_notify_fail,
        mock_event_failed_to_publish_signal,
        mock_should_persist_all_events,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify(
                *args, first_param="1", second_param="2"
            )

        original_func = jaiminho_django_test_project.send.notify.original_func
        mock_event_failed_to_publish_signal.assert_called_once_with(
            sender=original_func,
            event_payload=args[0],
            args=args,
            first_param="1",
            second_param="2",
        )
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_fail_with_parameters(
        self,
        mock_internal_notify_fail,
        mock_should_persist_all_events,
        encoder,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.delete_after_send", persist_all_events)
        args = ({"action": "a", "type": "t", "c": "d"},)
        param = {"param": 1}
        jaiminho_django_test_project.send.notify(*args, encoder=encoder, param=param)
        assert Event.objects.all().count() == 1
        event = Event.objects.first()
        assert event.sent_at is None
        assert event.stream is None
        assert dill.loads(event.kwargs)["encoder"] == Encoder
        assert dill.loads(event.kwargs)["param"] == param
        assert dill.loads(event.message) == args
        assert (
            dill.loads(event.function).__code__.co_code
            == jaiminho_django_test_project.send.notify.original_func.__code__.co_code
        )


class TestNotifyWithStream:
    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_send_to_stream_success_should_persist_all_events(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_to_stream(payload)

        assert Event.objects.all().count() == 1
        assert (
            Event.objects.get().stream
            == jaiminho_django_test_project.send.EXAMPLE_STREAM
        )
        assert "JAIMINHO-SAVE-TO-OUTBOX: Event created" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    def test_send_to_stream_success_should_persist_strategy(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_to_stream(payload)

        assert Event.objects.all().count() == 1
        assert Event.objects.get().strategy == publish_strategy

    @pytest.mark.parametrize("publish_strategy", (PublishStrategyType.KEEP_ORDER,))
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_send_to_stream_success_should_not_send_event_when_keep_order_strategy(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        persist_all_events,
        delete_after_send,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_to_stream(payload)

        assert not mock_internal_notify.called

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_to_stream_success_should_publish_event(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        publish_strategy,
        caplog,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(*args)

        assert len(callbacks) == 1
        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 1
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_to_stream_success_should_not_persist_all_events(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(*args)
        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 0
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_to_stream_success_should_delete_after_send(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_persist_all_events,
        mock_should_delete_after_send,
        caplog,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(*args)
            assert Event.objects.all().count() == 1
            event = Event.objects.get()
            assert event.sent_at is None

        mock_internal_notify.assert_called_once_with(*args)
        assert Event.objects.all().count() == 0
        mock_log_metric.assert_called_once_with("event-published", args[0], args=args)
        assert len(callbacks) == 1
        assert (
            "JAIMINHO-ON-COMMIT-HOOK: Event deleted after success send" in caplog.text
        )

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    def test_send_to_stream_success_when_should_not_delete_after_send(
        self,
        mock_log_metric,
        mock_internal_notify,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        caplog,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        payload = {"action": "a", "type": "t", "c": "d"}

        with freeze_time("2022-01-01"):
            with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
                jaiminho_django_test_project.send.notify_to_stream(payload)
            assert len(callbacks) == 1

        assert Event.objects.all().count() == 1
        event = Event.objects.first()
        assert (
            Event.objects.first().stream
            == jaiminho_django_test_project.send.EXAMPLE_STREAM
        )
        assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)
        assert "JAIMINHO-ON-COMMIT-HOOK: Event marked as sent" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_send_to_stream_fail(
        self,
        mock_log_metric,
        mock_internal_notify_fail,
        persist_all_events,
        delete_after_send,
        publish_strategy,
        mocker,
        caplog,
    ):
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(*args)

        mock_internal_notify_fail.assert_called_once_with(*args)
        assert Event.objects.all().count() == 1
        assert Event.objects.first().sent_at is None
        assert (
            Event.objects.first().stream
            == jaiminho_django_test_project.send.EXAMPLE_STREAM
        )
        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish", args[0], args=args
        )
        assert len(callbacks) == 1
        assert "JAIMINHO-ON-COMMIT-HOOK: Event failed to be published" in caplog.text

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        "exception",
        (AssertionError, AttributeError, Exception, SystemError, SystemExit),
    )
    def test_send_to_stream_fail_handles_multiple_exceptions_type(
        self,
        mock_log_metric,
        mock_internal_notify_fail,
        exception,
        publish_strategy,
        mocker,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)

        mock_internal_notify_fail.side_effect = exception

        args = ({"action": "a", "type": "t", "c": "d"},)
        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(*args)

        mock_internal_notify_fail.assert_called_once_with(*args)

        mock_log_metric.assert_called_once_with(
            "event-failed-to-publish", args[0], args=args
        )
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_to_stream_trigger_event_published_signal(
        self,
        mock_internal_notify,
        mock_event_published_signal,
        mock_should_persist_all_events,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(
                {"action": "a", "type": "t", "c": "d"}
            )
        mock_event_published_signal.assert_called_once()
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_to_stream_trigger_event_failed_to_publish_signal(
        self,
        mock_internal_notify_fail,
        mock_event_failed_to_publish_signal,
        mock_should_persist_all_events,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.persist_all_events", persist_all_events)

        with TestCase.captureOnCommitCallbacks(execute=True) as callbacks:
            jaiminho_django_test_project.send.notify_to_stream(
                {"action": "a", "type": "t", "c": "d"}
            )

        mock_event_failed_to_publish_signal.assert_called_once()
        assert len(callbacks) == 1

    @pytest.mark.parametrize(
        "publish_strategy", (PublishStrategyType.PUBLISH_ON_COMMIT,)
    )
    @pytest.mark.parametrize(
        ("delete_after_send", "persist_all_events"), ((True, False), (True, False))
    )
    def test_send_to_stream_fail_with_parameters(
        self,
        mock_internal_notify_fail,
        mock_should_persist_all_events,
        encoder,
        mocker,
        delete_after_send,
        persist_all_events,
        publish_strategy,
    ):
        mocker.patch("jaiminho.send.settings.publish_strategy", publish_strategy)
        mocker.patch("jaiminho.send.settings.delete_after_send", delete_after_send)
        mocker.patch("jaiminho.send.settings.delete_after_send", persist_all_events)
        args = ({"action": "a", "type": "t", "c": "d"},)
        param = {"param": 1}
        jaiminho_django_test_project.send.notify_to_stream(
            *args, encoder=encoder, param=param
        )
        assert Event.objects.all().count() == 1
        event = Event.objects.first()
        assert event.stream == jaiminho_django_test_project.send.EXAMPLE_STREAM
        assert event.sent_at is None
        assert dill.loads(event.kwargs)["encoder"] == Encoder
        assert dill.loads(event.kwargs)["param"] == param
        assert dill.loads(event.message) == args
        assert (
            dill.loads(event.function).__code__.co_code
            == jaiminho_django_test_project.send.notify.original_func.__code__.co_code
        )


class TestNofityWithStreamOverwritingStrategy:
    def test_send_to_stream_success_should_persist_all_events(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        caplog,
        mocker,
    ):
        strategy = KeepOrderStrategy()
        mocker.patch(
            "jaiminho.settings.publish_strategy", PublishStrategyType.PUBLISH_ON_COMMIT
        )
        create_publish_strategy_mock = mocker.patch(
            "jaiminho.send.create_publish_strategy",
            autospec=True,
            return_value=strategy,
        )

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_to_stream_overwriting_strategy(
                payload
            )

        create_publish_strategy_mock.assert_called_once_with(
            PublishStrategyType.KEEP_ORDER
        )
        assert Event.objects.all().count() == 1
        assert (
            Event.objects.get().stream
            == jaiminho_django_test_project.send.EXAMPLE_STREAM
        )
        assert "JAIMINHO-SAVE-TO-OUTBOX: Event created" in caplog.text

    def test_send_to_stream_should_persist_strategy(
        self,
        mock_internal_notify,
        mock_log_metric,
        mock_should_not_delete_after_send,
        mock_should_persist_all_events,
        caplog,
        mocker,
    ):
        strategy = KeepOrderStrategy()
        mocker.patch(
            "jaiminho.settings.publish_strategy", PublishStrategyType.PUBLISH_ON_COMMIT
        )
        create_publish_strategy_mock = mocker.patch(
            "jaiminho.send.create_publish_strategy",
            autospec=True,
            return_value=strategy,
        )

        payload = {"action": "a", "type": "t", "c": "d"}
        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_to_stream_overwriting_strategy(
                payload
            )

        create_publish_strategy_mock.assert_called_once_with(
            PublishStrategyType.KEEP_ORDER
        )
        assert Event.objects.all().count() == 1
        assert Event.objects.get().strategy == PublishStrategyType.KEEP_ORDER
