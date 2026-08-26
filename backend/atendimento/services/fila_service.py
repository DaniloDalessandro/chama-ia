"""
FilaService: ordenacao determinística da fila de atendimentos (secao 26 do
escopo): 1. regra critica confirmada, 2-6. P1..P4..nao classificado (e
revisao humana, nao listada explicitamente no spec -- tratada logo apos
"nao classificado", assuncao documentada), 7. maior indice AHP,
8. SLA mais proximo (FORA DE ESCOPO -- nao existe conceito de SLA em
lugar nenhum do sistema hoje), 9. maior tempo de espera.

Tudo resolvido num unico .order_by() do Django -- sem sort em Python --
incluindo o "tempo de espera" (calculado via ExpressionWrapper a partir de
criado_em, sem precisar de coluna armazenada).
"""

from django.db.models import Case, DurationField, ExpressionWrapper, F, IntegerField, QuerySet, Value, When
from django.utils import timezone

from ..models import Atendimento

_ORDEM_PRIORIDADE = {
    Atendimento.Prioridade.P1: 1,
    Atendimento.Prioridade.P2: 2,
    Atendimento.Prioridade.P3: 3,
    Atendimento.Prioridade.P4: 4,
    Atendimento.Prioridade.NAO_CLASSIFICADO: 5,
    # REVISAO_HUMANA nao e listada explicitamente na secao 26 -- tratada logo
    # apos NAO_CLASSIFICADO (assuncao documentada, nao uma leitura literal do spec).
    Atendimento.Prioridade.REVISAO_HUMANA: 6,
}

STATUS_EXCLUIDOS_DA_FILA = [
    Atendimento.StatusAtendimento.RESOLVIDO,
    Atendimento.StatusAtendimento.CANCELADO,
    Atendimento.StatusAtendimento.ENCAMINHADO_PARA_CHAMADO,
]


class FilaService:
    @staticmethod
    def get_fila_ordenada() -> QuerySet:
        agora = timezone.now()

        prioridade_ordem = Case(
            *[When(prioridade=codigo, then=Value(ordem)) for codigo, ordem in _ORDEM_PRIORIDADE.items()],
            default=Value(99),
            output_field=IntegerField(),
        )

        return (
            Atendimento.objects.exclude(status_atendimento__in=STATUS_EXCLUIDOS_DA_FILA)
            .annotate(
                _prioridade_ordem=prioridade_ordem,
                _tempo_espera=ExpressionWrapper(Value(agora) - F("criado_em"), output_field=DurationField()),
            )
            .order_by(
                "-regra_critica_confirmada",
                "_prioridade_ordem",
                F("indice_ahp").desc(nulls_last=True),
                # Secao 26, item 8 (SLA mais proximo) fica fora de escopo nesta
                # fase -- nao existe conceito de SLA no modelo hoje. Vai direto
                # do item 7 (indice AHP) para o item 9 (tempo de espera).
                "-_tempo_espera",
            )
        )
