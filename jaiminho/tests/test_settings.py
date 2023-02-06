from importlib import import_module
from importlib import reload

import pytest

from jaiminho.constants import PublishStrategyType


class TestSettings:
    @pytest.mark.parametrize(
        "publish_strategy",
        (PublishStrategyType.PUBLISH_ON_COMMIT, PublishStrategyType.KEEP_ORDER),
    )
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_load_settings(
        self, mocker, persist_all_events, delete_after_send, publish_strategy
    ):
        settings_mock = mocker.patch("django.conf.settings")
        time_to_delete = mocker.MagicMock()
        persist_all_events = True
        delete_after_send = True

        settings_mock.JAIMINHO_CONFIG = {
            "PERSIST_ALL_EVENTS": persist_all_events,
            "TIME_TO_DELETE": time_to_delete,
            "DELETE_AFTER_SEND": delete_after_send,
            "PUBLISH_STRATEGY": publish_strategy,
        }
        settings_module = import_module("jaiminho.settings")
        settings_module = reload(settings_module)

        assert getattr(settings_module, "persist_all_events") == persist_all_events
        assert getattr(settings_module, "time_to_delete") == time_to_delete
        assert getattr(settings_module, "delete_after_send") == delete_after_send
        assert getattr(settings_module, "publish_strategy") == publish_strategy
