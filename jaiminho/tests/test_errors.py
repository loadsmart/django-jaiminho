from django.core.signing import BadSignature

from jaiminho.errors import is_non_retryable


class TestIsNonRetryable:
    def test_bad_signature_is_non_retryable(self):
        assert is_non_retryable(BadSignature("tampered")) is True

    def test_module_not_found_error_is_non_retryable(self):
        assert is_non_retryable(ModuleNotFoundError()) is True

    def test_attribute_error_is_non_retryable(self):
        assert is_non_retryable(AttributeError()) is True

    def test_other_exceptions_are_not_non_retryable(self):
        assert is_non_retryable(ValueError()) is False

    def test_configured_exception_is_non_retryable(self, mocker):
        class MyCustomError(Exception):
            pass

        mocker.patch("jaiminho.settings.non_retryable_exceptions", (MyCustomError,))

        assert is_non_retryable(MyCustomError()) is True

    def test_configured_exceptions_replace_the_defaults(self, mocker):
        class MyCustomError(Exception):
            pass

        mocker.patch("jaiminho.settings.non_retryable_exceptions", (MyCustomError,))

        assert is_non_retryable(BadSignature("tampered")) is False
