from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class ChamadoPublicoRateThrottle(AnonRateThrottle):
    """
    Rate limit para criacao de chamados publicos.
    Limita requisicoes por IP para evitar spam/abuso.
    """

    rate = "10/hour"  # 10 chamados por hora por IP
    scope = "chamado_publico"

    def get_cache_key(self, request, view):
        # Usar IP como identificador
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident
        }


class ChamadoPublicoProcessarIARateThrottle(AnonRateThrottle):
    """
    Rate limit para processamento IA de chamados publicos.
    Mais generoso que o create pois e chamado automaticamente apos criar.
    """

    rate = "30/hour"
    scope = "chamado_publico_ia"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident
        }


class ChamadoConsultaRateThrottle(AnonRateThrottle):
    """
    Rate limit para consulta publica de chamados.
    """

    rate = "30/minute"  # 30 consultas por minuto por IP
    scope = "chamado_consulta"


class ChamadoAdminRateThrottle(UserRateThrottle):
    """
    Rate limit para operacoes administrativas.
    """

    rate = "1000/hour"  # 1000 operacoes por hora por usuario
    scope = "chamado_admin"
