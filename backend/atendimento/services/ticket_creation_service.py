"""
TicketCreationService: cria um Chamado a partir de um Atendimento nao
resolvido. Nunca e chamado automaticamente -- e sempre uma acao explicita
(endpoint/admin), disparada apenas quando o atendimento nao pode ser
resolvido dentro do proprio chat.

O atendimento original NUNCA e apagado nem "transformado fisicamente" -- ele
apenas transiciona para ENCAMINHADO_PARA_CHAMADO e permanece intacto,
acessivel via `chamado.atendimento_origem`.
"""

from django.db import transaction

from ..models import Atendimento

_PRIORIDADE_ATENDIMENTO_PARA_CHAMADO = {
    Atendimento.Prioridade.P1: "urgente",
    Atendimento.Prioridade.P2: "alta",
    Atendimento.Prioridade.P3: "media",
    Atendimento.Prioridade.P4: "baixa",
}


class TicketCreationService:
    @staticmethod
    @transaction.atomic
    def create_from_atendimento(atendimento: Atendimento, motivo: str, user=None):
        from chamados.models import Chamado

        mensagens = list(atendimento.mensagens.order_by("criado_em"))
        historico = "\n\n".join(
            f"[{mensagem.get_remetente_tipo_display()}] {mensagem.conteudo}" for mensagem in mensagens
        )
        descricao = historico or motivo or "Encaminhado a partir de um atendimento via chat."
        assunto = mensagens[0].conteudo[:80] if mensagens else f"Atendimento #{atendimento.id}"

        chamado = Chamado.objects.create(
            nome=atendimento.nome,
            email=atendimento.email,
            telefone=atendimento.telefone,
            cliente=atendimento.cliente,
            assunto=assunto,
            descricao=descricao,
            origem=Chamado.Origem.CHAT,
            prioridade=_PRIORIDADE_ATENDIMENTO_PARA_CHAMADO.get(atendimento.prioridade, "media"),
            atendimento_origem=atendimento,
            motivo_encaminhamento=motivo,
            prioridade_calculada_atendimento=atendimento.prioridade,
            created_by=user,
            updated_by=user,
        )

        atendimento.status_atendimento = Atendimento.StatusAtendimento.ENCAMINHADO_PARA_CHAMADO
        atendimento.atualizado_por = user
        atendimento.save(update_fields=["status_atendimento", "atualizado_por", "atualizado_em"])

        return chamado
