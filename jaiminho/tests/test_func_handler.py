import pytest

from jaiminho.func_handler import format_func_path, load_func_from_path
from jaiminho.tests.utils import foo


class TestFuncHandler:
    @pytest.fixture
    def mock_foo(self, mocker):
        return mocker.patch("jaiminho.tests.utils.foo")\


    @pytest.fixture
    def mock_bar(self, mocker):
        return mocker.patch("jaiminho.tests.utils.Bar")

    def test_func_handler(self):
        assert "jaiminho.tests.utils.foo" == format_func_path(foo)

    def test_func_handler_returns_default(self):
        assert format_func_path("") is None

    def test_load_func_from_path(self, mock_foo):
        path = "jaiminho.tests.utils.foo"

        fn = load_func_from_path(path)

        fn()
        mock_foo.assert_called_once()

    def test_load_class_from_path(self):
        path = "jaiminho.tests.utils.Bar"

        fn = load_func_from_path(path)

        obj = fn()
        assert obj.bar is True

    def test_raises_module_not_found_when_module_does_not_exist(self):
        path = "jaiminho.missing_module.utils.bar"

        with pytest.raises(ModuleNotFoundError):
            load_func_from_path(path)

    def test_raises_attribute_error_when_module_has_not_attribute(self):
        path = "jaiminho.tests.utils.missing_func"

        with pytest.raises(AttributeError):
            load_func_from_path(path)
