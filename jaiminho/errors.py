from django.core.signing import BadSignature

DEFAULT_NON_RETRYABLE_EXCEPTIONS = (BadSignature, ModuleNotFoundError, AttributeError)


def is_non_retryable(exception):
    from jaiminho import settings

    return isinstance(exception, settings.non_retryable_exceptions)
