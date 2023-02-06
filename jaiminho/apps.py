from django.apps import AppConfig
from django.utils import version


class JaiminhoConfig(AppConfig):
    if version.get_version() >= "3.2":
        default_auto_field = "django.db.models.BigAutoField"
    else:
        default_auto_field = "django.db.models.AutoField"
    name = "jaiminho"
