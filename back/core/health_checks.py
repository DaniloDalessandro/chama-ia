"""
Custom Health Checks para monitoramento de serviços.
"""

from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable
from celery.app.control import Inspect


class CeleryHealthCheck(BaseHealthCheckBackend):
    """
    Health check para verificar se Celery workers estão rodando.
    """

    critical_service = True

    def check_status(self):
        """
        Verifica se há workers Celery ativos.
        """
        try:
            from core.celery import app
            inspect = Inspect(app=app)

            # Verificar workers ativos
            stats = inspect.stats()

            if not stats:
                self.add_error(
                    ServiceUnavailable("Nenhum Celery worker ativo detectado")
                )
            else:
                # Workers encontrados
                worker_count = len(stats)
                self.add_message(f"{worker_count} Celery worker(s) ativo(s)")

        except Exception as e:
            self.add_error(
                ServiceUnavailable(f"Erro ao verificar Celery workers: {str(e)}")
            )

    def identifier(self):
        return "Celery Workers"
