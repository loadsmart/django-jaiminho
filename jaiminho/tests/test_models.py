from datetime import datetime

import pytest
from dateutil.tz import UTC
from freezegun import freeze_time

from jaiminho.tests.factories import EventFactory


@pytest.mark.django_db
class TestEvent:
    def test_mark_as_sent(self):
        event = EventFactory()
        assert event.sent_at is None

        with freeze_time("2022-01-01"):
            event.mark_as_sent()
            assert event.sent_at == datetime(2022, 1, 1, tzinfo=UTC)
