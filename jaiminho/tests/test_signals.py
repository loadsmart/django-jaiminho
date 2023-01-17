from jaiminho.signals import get_event_payload


class TestGetEventPayload:
    def test_success_when_args_is_tuple(self):
        assert get_event_payload(({"a": 1},)) == {"a": 1}

    def test_return_empty_dict_when_args_empty_iterable(self):
        assert get_event_payload(()) == {}

    def test_return_empty_dict_when_args_not_iterable(self):
        assert get_event_payload(1) == {}
