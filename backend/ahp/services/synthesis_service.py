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

    @staticmethod
    def compute_p_fuzzy(
        pesos_criterios: dict,
        prioridades_por_criterio: dict,
        intensidades_escolhidas: dict,
        confiancas: dict,
        alpha: float = 0.20,
    ) -> tuple:
        """
        Extensao fuzzy ponderada por confianca (AHP Fuzzy Ponderada por Confianca).

        Para cada criterio i, constroi um numero fuzzy triangular (l, m, u) a partir
        da prioridade local m = p_i,a e da confianca c_i reportada pelo agente de IA:

            l_i = max(0,         m_i - alpha * (1 - c_i))
            u_i = min(p_i_max,   m_i + alpha * (1 - c_i))

        Quanto menor a confianca, mais largo o intervalo. Com confianca = 1.0 o
        intervalo colapsa: l = m = u (retrocompativel com compute_p).

        Argumentos:
            pesos_criterios           -- {criterio_codigo: peso_w}
            prioridades_por_criterio  -- {criterio_codigo: {intensidade_codigo: peso}}
            intensidades_escolhidas   -- {criterio_codigo: intensidade_codigo}
            confiancas                -- {criterio_codigo: float 0-1}
            alpha                     -- hiperparametro de escala (default 0.20)

        Retorna (P_l, P_m, P_u, contribuicoes_fuzzy) onde:
            P_m e identico ao P(a) de compute_p -- retrocompativel no valor central.
            contribuicoes_fuzzy = {criterio_codigo: (contrib_l, contrib_m, contrib_u)}
        """
        contribuicoes_fuzzy = {}
        p_l = p_m = p_u = 0.0

        for codigo_criterio, peso in pesos_criterios.items():
            codigo_intensidade = intensidades_escolhidas.get(codigo_criterio)
            if codigo_intensidade is None:
                raise ValueError(f"Nenhuma intensidade escolhida para o criterio '{codigo_criterio}'.")

            prioridades = prioridades_por_criterio.get(codigo_criterio, {})
            m = AHPIntensityService.contribution_for(codigo_intensidade, prioridades)
            c = float(confiancas.get(codigo_criterio, 1.0))
            p_max_criterio = max(prioridades.values()) if prioridades else m

            spread = alpha * (1.0 - c)
            l = max(0.0, m - spread)
            u = min(p_max_criterio, m + spread)

            contribuicoes_fuzzy[codigo_criterio] = (peso * l, peso * m, peso * u)
            p_l += peso * l
            p_m += peso * m
            p_u += peso * u

        return p_l, p_m, p_u, contribuicoes_fuzzy
