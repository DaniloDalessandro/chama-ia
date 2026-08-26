"""
Throttles para os endpoints publicos/anonimos de atendimento -- espelha
`chamados/throttling.py::ChamadoPublicoRateThrottle`.
"""

from rest_framework.throttling import AnonRateThrottle


class AtendimentoPublicoRateThrottle(AnonRateThrottle):
    """Rate limit para criacao de atendimentos publicos (chat anonimo). Por IP."""

    rate = "10/hour"
    scope = "atendimento_publico"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AtendimentoPublicoConsultaRateThrottle(AnonRateThrottle):
    """
    Rate limit para consulta/polling REST (fallback) de atendimentos
    publicos. Mais generoso que a criacao, pois pode ser chamado
    repetidamente enquanto o chat esta aberto.
    """

    rate = "30/minute"
    scope = "atendimento_publico_consulta"
