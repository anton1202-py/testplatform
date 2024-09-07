from django.apps import AppConfig


class UnitEconomicsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unit_economics'
    verbose_name = 'Unit экономика'

    def ready(self):
        import unit_economics.signals  # Импортируйте файл с сигналами
