from importlib import import_module
from importlib import reload

import pytest


class TestSettings:
    @pytest.mark.parametrize(
        ("persist_all_events", "delete_after_send"), ((True, False), (True, False))
    )
    def test_load_settings(self, mocker, persist_all_events, delete_after_send):
        settings_mock = mocker.patch("django.conf.settings")
        time_to_delete = mocker.MagicMock()
        persist_all_events = True
        delete_after_send = True

        settings_mock.JAIMINHO_CONFIG = {
            "PERSIST_ALL_EVENTS": persist_all_events,
            "TIME_TO_DELETE": time_to_delete,
            "DELETE_AFTER_SEND": delete_after_send,
        }
        settings_module = import_module("jaiminho.settings")
        settings_module = reload(settings_module)

        assert getattr(settings_module, "persist_all_events") == persist_all_events
        assert getattr(settings_module, "time_to_delete") == time_to_delete
        assert getattr(settings_module, "delete_after_send") == delete_after_send
