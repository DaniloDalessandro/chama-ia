from django.apps import AppConfig


class ChamadosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chamados"

    def ready(self):
        """
        Importa signals quando o app esta pronto.
        Isso registra os receivers automaticamente.
        """
        import chamados.signals  # noqa: F401
