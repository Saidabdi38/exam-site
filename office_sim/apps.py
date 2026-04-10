from django.apps import AppConfig


class OfficeSimConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'office_sim'

    def ready(self):
        import office_sim.signals
