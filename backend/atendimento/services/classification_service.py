"""
ServicePriorityClassificationService: aplica as regras de negocio da fila
(bandas fixas P1-P4 + revisao_humana) sobre o resultado matematico do AHP.

Criterios inconclusivos ou ausentes disparam revisao_humana imediatamente.
Quando as confiancas do agente sao fornecidas, o intervalo fuzzy [l, u] e
calculado; se esse intervalo cruzar uma fronteira de banda, o caso tambem
vai para revisao_humana.

A matematica em si (pesos, prioridades locais, P(a), Indice(a)) ja foi
calculada e congelada em VersaoAHP no momento da ativacao -- este servico
apenas LE esses valores congelados e sintetiza o indice para um atendimento
especifico. Nao recalcula autovetores/CR aqui.
"""

from dataclasses import dataclass, field

from ahp.models import Intensidade, VersaoAHP
from ahp.services.normalization_service import AHPNormalizationService
from ahp.services.synthesis_service import AHPSynthesisService
from ahp.services.version_service import AHPVersionService

from ..models import Atendimento

_BANDAS = (
    (80.0, Atendimento.Prioridade.P1),
    (60.0, Atendimento.Prioridade.P2),
    (35.0, Atendimento.Prioridade.P3),
)

# Margem de transicao fuzzy: se o indice cair dentro de MARGEM_TRANSICAO pontos
# de qualquer fronteira de banda, o caso vai para revisao_humana em vez de ser
# classificado com falsa certeza. Elimina o problema de fronteiras instáveis.
MARGEM_TRANSICAO = 3.0
_FRONTEIRAS = tuple(limite for limite, _ in _BANDAS)


@dataclass
class ResultadoClassificacao:
    prioridade: str
    indice: float | None
    pesos_criterios: dict
    prioridades_locais: dict
    intensidades: dict
    contribuicoes: dict
    p: float
    p_max: float | None
    revisao_humana: bool = False
    motivos_revisao_humana: list = field(default_factory=list)
    erros: list = field(default_factory=list)
    # Campos fuzzy (preenchidos quando confiancas sao fornecidas)
    indice_l: float | None = None
    indice_u: float | None = None
    contribuicoes_fuzzy: dict = field(default_factory=dict)


class NenhumaVersaoAtivaError(Exception):
    """Nao ha VersaoAHP ativa -- nao e possivel classificar nenhum atendimento."""


class ServicePriorityClassificationService:
    @staticmethod
    def classificar_por_indice(indice: float) -> str:
        for limite, prioridade in _BANDAS:
            if indice >= limite:
                return prioridade
        return Atendimento.Prioridade.P4

    @staticmethod
    def fronteira_mais_proxima(indice: float) -> float | None:
        """Retorna a fronteira mais próxima se o índice estiver dentro da MARGEM_TRANSICAO, senão None."""
        for fronteira in _FRONTEIRAS:
            if abs(indice - fronteira) <= MARGEM_TRANSICAO:
                return fronteira
        return None

    @staticmethod
    def classify(atendimento: Atendimento, versao_ahp: VersaoAHP = None) -> ResultadoClassificacao:
        versao_ahp = versao_ahp or AHPVersionService.get_versao_ativa()
        if versao_ahp is None:
            raise NenhumaVersaoAtivaError("Nao ha nenhuma VersaoAHP ativa no momento.")

        avaliacoes = list(atendimento.avaliacoes.select_related("criterio", "intensidade"))
        intensidades_escolhidas = {av.criterio.codigo: av.intensidade.codigo for av in avaliacoes}

        return ServicePriorityClassificationService._classify_common(versao_ahp, intensidades_escolhidas)

    @staticmethod
    def classify_from_intensidades(
        versao_ahp: VersaoAHP,
        intensidades: dict,
        confiancas: dict | None = None,
        alpha: float = 0.20,
    ) -> ResultadoClassificacao:
        """Variante que aceita um dict {criterio_codigo: intensidade_codigo} diretamente,
        sem tocar o banco -- usada por comandos administrativos/testes sinteticos.

        confiancas: {criterio_codigo: float 0-1} -- quando fornecido, ativa o calculo
        fuzzy (indice_l / indice_u) apenas para fins informativos.
        alpha: hiperparametro de escala fuzzy (default 0.20).
        """
        return ServicePriorityClassificationService._classify_common(
            versao_ahp, intensidades, confiancas=confiancas, alpha=alpha
        )

    @staticmethod
    def _classify_common(
        versao_ahp: VersaoAHP,
        intensidades_escolhidas: dict,
        confiancas: dict | None = None,
        alpha: float = 0.20,
    ) -> ResultadoClassificacao:
        pesos_criterios = versao_ahp.pesos_criterios or {}
        prioridades_locais = versao_ahp.prioridades_intensidades or {}

        # Criterios inconclusivos ou ausentes disparam revisao humana imediata.
        motivos_revisao = []
        for cod in pesos_criterios:
            val = intensidades_escolhidas.get(cod)
            if val is None:
                motivos_revisao.append(f"criterio ausente: {cod}")
            elif val == Intensidade.Codigo.INCONCLUSIVA:
                motivos_revisao.append(f"intensidade inconclusiva: {cod}")

        if motivos_revisao:
            return ResultadoClassificacao(
                prioridade=Atendimento.Prioridade.REVISAO_HUMANA,
                indice=None,
                pesos_criterios=pesos_criterios,
                prioridades_locais=prioridades_locais,
                intensidades=intensidades_escolhidas,
                contribuicoes={},
                p=0.0,
                p_max=versao_ahp.p_max,
                revisao_humana=True,
                motivos_revisao_humana=motivos_revisao,
            )

        p, contribuicoes = AHPSynthesisService.compute_p(
            pesos_criterios, prioridades_locais, intensidades_escolhidas
        )
        indice = AHPNormalizationService.compute_indice(p, versao_ahp.p_max)
        prioridade = ServicePriorityClassificationService.classificar_por_indice(indice)

        # Zona de transicao fuzzy deterministica: se o indice estiver a menos de
        # MARGEM_TRANSICAO pontos de qualquer fronteira, classificar como revisao_humana
        # independentemente de confiancas (elimina instabilidade de fronteira).
        fronteira = ServicePriorityClassificationService.fronteira_mais_proxima(indice)
        if fronteira is not None:
            banda_abaixo = ServicePriorityClassificationService.classificar_por_indice(fronteira - MARGEM_TRANSICAO - 0.01)
            return ResultadoClassificacao(
                prioridade=Atendimento.Prioridade.REVISAO_HUMANA,
                indice=indice,
                pesos_criterios=pesos_criterios,
                prioridades_locais=prioridades_locais,
                intensidades=intensidades_escolhidas,
                contribuicoes=contribuicoes,
                p=p,
                p_max=versao_ahp.p_max,
                revisao_humana=True,
                motivos_revisao_humana=[
                    f"zona de transicao: indice={indice:.1f} esta a "
                    f"{abs(indice - fronteira):.1f} pontos da fronteira {fronteira:.0f} "
                    f"(margem={MARGEM_TRANSICAO})"
                ],
            )

        # Calculo fuzzy
        indice_l = indice_u = None
        contribuicoes_fuzzy = {}
        if confiancas:
            p_l, _p_m, p_u, contribuicoes_fuzzy = AHPSynthesisService.compute_p_fuzzy(
                pesos_criterios, prioridades_locais, intensidades_escolhidas, confiancas, alpha
            )
            indice_l = AHPNormalizationService.compute_indice(p_l, versao_ahp.p_max)
            indice_u = AHPNormalizationService.compute_indice(p_u, versao_ahp.p_max)

            # Se o intervalo fuzzy cruza uma fronteira de banda -> revisao humana
            banda_l = ServicePriorityClassificationService.classificar_por_indice(indice_l)
            banda_u = ServicePriorityClassificationService.classificar_por_indice(indice_u)
            if banda_l != banda_u:
                return ResultadoClassificacao(
                    prioridade=Atendimento.Prioridade.REVISAO_HUMANA,
                    indice=indice,
                    pesos_criterios=pesos_criterios,
                    prioridades_locais=prioridades_locais,
                    intensidades=intensidades_escolhidas,
                    contribuicoes=contribuicoes,
                    p=p,
                    p_max=versao_ahp.p_max,
                    revisao_humana=True,
                    motivos_revisao_humana=[
                        f"ambiguidade fuzzy: indice_l={indice_l:.1f} ({banda_l}) != indice_u={indice_u:.1f} ({banda_u})"
                    ],
                    indice_l=indice_l,
                    indice_u=indice_u,
                    contribuicoes_fuzzy=contribuicoes_fuzzy,
                )

        return ResultadoClassificacao(
            prioridade=prioridade,
            indice=indice,
            pesos_criterios=pesos_criterios,
            prioridades_locais=prioridades_locais,
            intensidades=intensidades_escolhidas,
            contribuicoes=contribuicoes,
            p=p,
            p_max=versao_ahp.p_max,
            revisao_humana=False,
            indice_l=indice_l,
            indice_u=indice_u,
            contribuicoes_fuzzy=contribuicoes_fuzzy,
        )
