"""
ServicePriorityClassificationService: aplica as regras de negocio da fila
(bandas fixas P1-P4, revisao humana) sobre o resultado matematico do AHP.

A matematica em si (pesos, prioridades locais, P(a), Indice(a)) ja foi
calculada e congelada em VersaoAHP no momento da ativacao -- este servico
apenas LE esses valores congelados e sintetiza o indice para um atendimento
especifico. Nao recalcula autovetores/CR aqui.

Regra critica (Agente 5, fases seguintes) e registrada separadamente e NUNCA
altera a matematica do AHP nem o valor de `prioridade` -- ela apenas afeta a
ORDENACAO da fila (responsabilidade de uma fase futura), conforme o escopo:
"Uma regra critica pode fazer o atendimento subir para o topo da fila, mas
deve ser registrada separadamente da matematica do AHP."
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


@dataclass
class ResultadoClassificacao:
    prioridade: str
    indice: float | None
    pesos_criterios: dict
    prioridades_locais: dict
    intensidades: dict
    contribuicoes: dict
    p: float | None
    p_max: float | None
    revisao_humana: bool
    motivos_revisao_humana: list = field(default_factory=list)
    erros: list = field(default_factory=list)


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
    def classify(atendimento: Atendimento, versao_ahp: VersaoAHP = None) -> ResultadoClassificacao:
        versao_ahp = versao_ahp or AHPVersionService.get_versao_ativa()
        if versao_ahp is None:
            raise NenhumaVersaoAtivaError("Nao ha nenhuma VersaoAHP ativa no momento.")

        avaliacoes = list(atendimento.avaliacoes.select_related("criterio", "intensidade"))
        intensidades_escolhidas = {av.criterio.codigo: av.intensidade.codigo for av in avaliacoes}

        return ServicePriorityClassificationService._classify_common(versao_ahp, intensidades_escolhidas)

    @staticmethod
    def classify_from_intensidades(versao_ahp: VersaoAHP, intensidades: dict) -> ResultadoClassificacao:
        """Variante que aceita um dict {criterio_codigo: intensidade_codigo} diretamente,
        sem tocar o banco -- usada por comandos administrativos/testes sinteticos."""
        return ServicePriorityClassificationService._classify_common(versao_ahp, intensidades)

    @staticmethod
    def _classify_common(versao_ahp: VersaoAHP, intensidades_escolhidas: dict) -> ResultadoClassificacao:
        pesos_criterios = versao_ahp.pesos_criterios or {}
        prioridades_locais = versao_ahp.prioridades_intensidades or {}

        motivos_revisao_humana = []
        for codigo_criterio in pesos_criterios:
            codigo_intensidade = intensidades_escolhidas.get(codigo_criterio)
            if codigo_intensidade is None:
                motivos_revisao_humana.append(f"Dado ausente: nenhuma avaliacao para o criterio '{codigo_criterio}'.")
            elif codigo_intensidade == Intensidade.Codigo.INCONCLUSIVA:
                motivos_revisao_humana.append(f"Intensidade inconclusiva no criterio '{codigo_criterio}'.")

        if motivos_revisao_humana:
            return ResultadoClassificacao(
                prioridade=Atendimento.Prioridade.REVISAO_HUMANA,
                indice=None,
                pesos_criterios=pesos_criterios,
                prioridades_locais=prioridades_locais,
                intensidades=intensidades_escolhidas,
                contribuicoes={},
                p=None,
                p_max=versao_ahp.p_max,
                revisao_humana=True,
                motivos_revisao_humana=motivos_revisao_humana,
            )

        p, contribuicoes = AHPSynthesisService.compute_p(pesos_criterios, prioridades_locais, intensidades_escolhidas)
        indice = AHPNormalizationService.compute_indice(p, versao_ahp.p_max)
        prioridade = ServicePriorityClassificationService.classificar_por_indice(indice)

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
        )
