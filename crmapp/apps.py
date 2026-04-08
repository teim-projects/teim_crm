from django.apps import AppConfig


class CrmappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crmapp'


    def ready(self):
        import crmapp.signals
