from django.apps import AppConfig


class ExamsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "exams"

    def ready(self):
        # Register signals (auto-create Teachers group)
        from . import signals  # noqa: F401
