from datetime import timedelta
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

try:
    jaiminho_settings = getattr(settings, "jaiminho")
except AttributeError:
    jaiminho_settings = {}

persist_all_events = jaiminho_settings.get("PERSIST_ALL_EVENTS", False)
default_encoder = jaiminho_settings.get("DEFAULT_ENCODER", DjangoJSONEncoder)
time_to_delete = jaiminho_settings.get("TIME_TO_DELETE", timedelta(days=14))
