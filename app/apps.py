from django.apps import AppConfig



class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        """Executado quando a aplicação Django está pronta"""
        import app.signals  # noqa: F401

