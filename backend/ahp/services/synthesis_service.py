"""
AHPSynthesisService: sintese final do AHP por mensuracao absoluta.

P(a) = soma(w_i * p_i,a) sobre todos os criterios da hierarquia.

Este servico e puro (sem ORM, sem conceito de "P1-P4"/cores -- essas regras
de negocio pertencem ao app `atendimento`).
"""

from .intensity_service import AHPIntensityService


class AHPSynthesisService:
    @staticmethod
    def compute_p(pesos_criterios: dict, prioridades_por_criterio: dict, intensidades_escolhidas: dict) -> tuple:
        """
        pesos_criterios: {criterio_codigo: peso}
        prioridades_por_criterio: {criterio_codigo: {intensidade_codigo: peso}}
        intensidades_escolhidas: {criterio_codigo: intensidade_codigo}

        Retorna (P(a), contribuicoes) onde contribuicoes = {criterio_codigo: w_i * p_i,a}.

        Levanta ValueError se alguma intensidade escolhida for INCONCLUSIVA -- o
        chamador (ServicePriorityClassificationService) deve checar isso ANTES de
        chamar este metodo e desviar para revisao humana.
        """
        contribuicoes = {}
        p_total = 0.0

        for codigo_criterio, peso in pesos_criterios.items():
            codigo_intensidade = intensidades_escolhidas.get(codigo_criterio)
            if codigo_intensidade is None:
                raise ValueError(f"Nenhuma intensidade escolhida para o criterio '{codigo_criterio}'.")

            prioridades = prioridades_por_criterio.get(codigo_criterio, {})
            contribuicao = peso * AHPIntensityService.contribution_for(codigo_intensidade, prioridades)
            contribuicoes[codigo_criterio] = contribuicao
            p_total += contribuicao

        return p_total, contribuicoes

    @staticmethod
    def compute_p_max(pesos_criterios: dict, prioridades_por_criterio: dict) -> float:
        """P_max = soma(w_i * max(p_i,a entre as intensidades comparaveis)) -- teto teorico."""
        p_max = 0.0
        for codigo_criterio, peso in pesos_criterios.items():
            prioridades = prioridades_por_criterio.get(codigo_criterio, {})
            if not prioridades:
                continue
            p_max += peso * max(prioridades.values())
        return p_max
