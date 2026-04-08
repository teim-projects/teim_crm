from django.apps import AppConfig


class NewInventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'new_inventory'

    def ready(self):
        import new_inventory.signals  
