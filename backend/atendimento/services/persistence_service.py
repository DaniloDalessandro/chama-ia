"""
ServicePersistenceService: grava o resultado de uma classificacao de forma
atomica -- cria a linha (imutavel) de AuditoriaClassificacao e atualiza o
Atendimento correspondente na mesma transacao.
"""

from django.db import transaction

from ahp.services.consistency_service import RANDOM_INDEX

from ..models import Atendimento, AuditoriaClassificacao
from .audit_service import AuditService
from .classification_service import ResultadoClassificacao

_CORES_PRIORIDADE = {
    Atendimento.Prioridade.P1: "#DC2626",
    Atendimento.Prioridade.P2: "#EA580C",
    Atendimento.Prioridade.P3: "#CA8A04",
    Atendimento.Prioridade.P4: "#16A34A",
    Atendimento.Prioridade.NAO_CLASSIFICADO: "#64748B",
    Atendimento.Prioridade.REVISAO_HUMANA: "#7C3AED",
}


class ServicePersistenceService:
    @staticmethod
    @transaction.atomic
    def persist(atendimento: Atendimento, resultado: ResultadoClassificacao, versao_ahp, user=None) -> AuditoriaClassificacao:
        matriz_criterios, matriz_intensidades = AuditService.snapshot_matrizes(versao_ahp)
        n_criterios = len(resultado.pesos_criterios)
        ri = RANDOM_INDEX.get(n_criterios, 0.0)

        auditoria = AuditoriaClassificacao.objects.create(
            atendimento=atendimento,
            versao_ahp=versao_ahp,
            versao_hierarquia=versao_ahp.numero_versao,
            versao_criterios={"codigos": list(resultado.pesos_criterios.keys())},
            versao_intensidades={"prioridades_locais": resultado.prioridades_locais},
            versao_matriz_criterios=matriz_criterios,
            versao_matriz_intensidades=matriz_intensidades,
            pesos_criterios=resultado.pesos_criterios,
            lambda_max=versao_ahp.lambda_max_criterios,
            ci=versao_ahp.ci_criterios,
            ri=ri,
            cr=versao_ahp.cr_criterios,
            prioridades_locais=resultado.prioridades_locais,
            intensidades=resultado.intensidades,
            contribuicoes=resultado.contribuicoes,
            indice=resultado.indice,
            prioridade=resultado.prioridade,
            classificacao_cor=_CORES_PRIORIDADE.get(resultado.prioridade, "#64748B"),
            regra_critica=atendimento.regra_critica_confirmada,
            erros=resultado.erros or resultado.motivos_revisao_humana,
            criado_por=user,
        )

        atendimento.prioridade = resultado.prioridade
        atendimento.indice_ahp = resultado.indice
        atendimento.versao_ahp_utilizada = versao_ahp
        atendimento.analise_ia_status = Atendimento.AnaliseIAStatus.CONCLUIDA
        atendimento.atualizado_por = user
        atendimento.save(
            update_fields=["prioridade", "indice_ahp", "versao_ahp_utilizada", "analise_ia_status", "atualizado_por", "atualizado_em"]
        )

        return auditoria
