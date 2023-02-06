import json
import os
import pytest
import shutil
from django.test import TestCase
from django.core.management import call_command

from jaiminho_django_test_project.management.commands import validate_events_relay
from jaiminho.constants import PublishStrategyType
from jaiminho.models import Event
import jaiminho_django_test_project.send


EVENTS_FOLDER_PATH = "./outbox_events_confirmation"


@pytest.fixture
def events_confirmation_folder():
    if os.path.exists(EVENTS_FOLDER_PATH):
        shutil.rmtree(EVENTS_FOLDER_PATH)
    os.mkdir(EVENTS_FOLDER_PATH)
    yield
    if os.path.exists(EVENTS_FOLDER_PATH):
        shutil.rmtree(EVENTS_FOLDER_PATH)


@pytest.mark.django_db
class TestSendToOutbox:
    def test_should_relay_when_keep_order_strategy_from_decorator(
        self, mocker, events_confirmation_folder
    ):
        mocker.patch(
            "jaiminho.settings.publish_strategy", PublishStrategyType.PUBLISH_ON_COMMIT
        )
        assert Event.objects.count() == 0

        first_args = [{"some": "data"}]
        second_args = [{"other": "data"}]
        first_file_path = f"{EVENTS_FOLDER_PATH}/event_1.json"
        second_file_path = f"{EVENTS_FOLDER_PATH}/event_2.json"

        with TestCase.captureOnCommitCallbacks(execute=True):
            jaiminho_django_test_project.send.notify_functional_to_stream_overwriting_strategy(
                *first_args, filepath=first_file_path
            )
            jaiminho_django_test_project.send.notify_functional_to_stream_overwriting_strategy(
                *second_args, filepath=second_file_path
            )

        assert Event.objects.count() == 2
        outbox_events = Event.objects.all()

        self.assertEvent(outbox_events[0])
        self.assertEvent(outbox_events[1])

        call_command(
            validate_events_relay.Command(),
            run_in_loop=False,
            stream=jaiminho_django_test_project.send.EXAMPLE_STREAM,
        )

        relayed_events = Event.objects.all().order_by("id")
        assert relayed_events.count() == 2
        for event in relayed_events:
            assert event.sent_at is not None
        assert relayed_events[0].sent_at < relayed_events[1].sent_at

        assert os.path.exists(first_file_path)
        assert os.path.exists(second_file_path)

        first_file = open(first_file_path)
        second_file = open(second_file_path)
        assert json.load(first_file) == first_args
        assert json.load(second_file) == second_args

    def assertEvent(self, event):
        assert event.strategy == PublishStrategyType.KEEP_ORDER
        assert event.stream == jaiminho_django_test_project.send.EXAMPLE_STREAM
        assert event.sent_at is None
