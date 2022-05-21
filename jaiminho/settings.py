from django.conf import settings

try:
    jaiminho_settings = getattr(settings, "jaiminho")
except AttributeError:
    jaiminho_settings = {}

persist_all_events = jaiminho_settings.get("PERSIST_ALL_EVENTS", False)
