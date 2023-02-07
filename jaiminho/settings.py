from datetime import timedelta
import sentry_sdk
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

from jaiminho.constants import PublishStrategyType

try:
    jaiminho_settings = getattr(settings, "JAIMINHO_CONFIG")
except AttributeError:
    jaiminho_settings = {}

persist_all_events = jaiminho_settings.get("PERSIST_ALL_EVENTS", False)
time_to_delete = jaiminho_settings.get("TIME_TO_DELETE", timedelta(days=7))
delete_after_send = jaiminho_settings.get("DELETE_AFTER_SEND", False)
publish_strategy = jaiminho_settings.get(
    "PUBLISH_STRATEGY", PublishStrategyType.PUBLISH_ON_COMMIT
)

default_capture_exception = jaiminho_settings.get(
    "DEFAULT_CAPTURE_EXCEPTION", sentry_sdk.capture_exception
)
