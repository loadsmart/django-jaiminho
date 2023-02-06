from django.apps import AppConfig


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jaiminho_django_test_project.app"

    def ready(self):
        import jaiminho_django_test_project.app.signals  # noqa
