"""
Throttling (Rate Limiting) personalizado para proteção contra ataques.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limit específico para tentativas de login.
    Previne ataques de brute-force.

    Limite: 5 tentativas por minuto por IP
    """
    scope = 'login'
    rate = '5/min'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate limit para requisições de reset de senha.
    Previne spam e ataques.

    Limite: 3 tentativas por hora por IP
    """
    scope = 'password_reset'
    rate = '3/hour'


class AuthenticatedUserRateThrottle(UserRateThrottle):
    """
    Rate limit geral para usuários autenticados.

    Limite: 1000 requisições por hora
    """
    scope = 'authenticated'
    rate = '1000/hour'


class StrictAnonRateThrottle(AnonRateThrottle):
    """
    Rate limit estrito para endpoints públicos sensíveis.

    Limite: 10 requisições por minuto por IP
    """
    scope = 'strict_anon'
    rate = '10/min'
