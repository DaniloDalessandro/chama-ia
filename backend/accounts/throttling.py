"""
Throttling (Rate Limiting) personalizado para proteção contra ataques.
"""
import logging
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class _FailOpenMixin:
    """Permite requisição (fail-open) se o cache estiver indisponível."""
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.warning("Throttle cache indisponível — requisição permitida sem rate-limit.")
            return True


class LoginRateThrottle(_FailOpenMixin, AnonRateThrottle):
    """
    Rate limit específico para tentativas de login.
    Previne ataques de brute-force.

    Limite: 5 tentativas por minuto por IP
    """
    scope = 'login'
    rate = '5/min'


class PasswordResetRateThrottle(_FailOpenMixin, AnonRateThrottle):
    """
    Rate limit para requisições de reset de senha.
    Previne spam e ataques.

    Limite: 3 tentativas por hora por IP
    """
    scope = 'password_reset'
    rate = '3/hour'


class AuthenticatedUserRateThrottle(_FailOpenMixin, UserRateThrottle):
    """
    Rate limit geral para usuários autenticados.

    Limite: 1000 requisições por hora
    """
    scope = 'authenticated'
    rate = '1000/hour'


class StrictAnonRateThrottle(_FailOpenMixin, AnonRateThrottle):
    """
    Rate limit estrito para endpoints públicos sensíveis.

    Limite: 10 requisições por minuto por IP
    """
    scope = 'strict_anon'
    rate = '10/min'
