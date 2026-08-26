from rest_framework import serializers

from .models import (
    AnexoAtendimento,
    Atendimento,
    AuditoriaClassificacao,
    AvaliacaoCriterioAtendimento,
    MensagemAtendimento,
    RegraCriticaAtendimento,
    RevisaoHumanaAtendimento,
)
from .services.waiting_time_service import WaitingTimeService


class AtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atendimento
        fields = [
            "id", "session_token", "origem", "status_atendimento", "prioridade", "analise_ia_status", "indice_ahp",
            "regra_critica_confirmada", "versao_ahp_utilizada", "assunto", "resumo", "servico_afetado", "atendente",
            "nome", "email", "telefone", "cliente",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]
        read_only_fields = [
            "session_token", "origem", "prioridade", "analise_ia_status", "indice_ahp", "regra_critica_confirmada",
            "versao_ahp_utilizada", "assunto", "resumo", "servico_afetado", "atendente",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]


class MensagemAtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensagemAtendimento
        fields = ["id", "atendimento", "remetente_tipo", "conteudo", "criado_em"]
        read_only_fields = ["atendimento", "criado_em"]


class AnexoAtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnexoAtendimento
        fields = ["id", "atendimento", "arquivo", "nome_original", "tipo_arquivo", "tamanho", "mime_type", "criado_em"]
        read_only_fields = ["atendimento", "criado_em"]


class AvaliacaoCriterioAtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvaliacaoCriterioAtendimento
        fields = [
            "id", "atendimento", "criterio", "intensidade", "evidencia", "justificativa",
            "origem", "confianca", "dados_ausentes", "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]
        read_only_fields = ["atendimento", "criado_em", "criado_por", "atualizado_em", "atualizado_por"]


class RevisaoHumanaAtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevisaoHumanaAtendimento
        fields = ["id", "atendimento", "prioridade_anterior", "nova_prioridade", "responsavel", "justificativa", "criado_em"]
        read_only_fields = ["atendimento", "prioridade_anterior", "responsavel", "criado_em"]


class AuditoriaClassificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditoriaClassificacao
        fields = "__all__"


class RegraCriticaAtendimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegraCriticaAtendimento
        fields = ["id", "atendimento", "criterio_gatilho", "termo_gatilho", "confirmada", "justificativa", "origem", "criado_em"]


class AtendimentoDetailPublicSerializer(serializers.ModelSerializer):
    """
    Serializer publica/anonima do atendimento -- mesmo espirito de card da
    AtendimentoFilaSerializer, mas NUNCA inclui AuditoriaClassificacao (pesos,
    matrizes) nem qualquer outro calculo interno do AHP.
    """

    tempo_espera_minutos = serializers.SerializerMethodField()
    sla = serializers.SerializerMethodField()

    class Meta:
        model = Atendimento
        fields = [
            "id", "nome", "assunto", "resumo", "servico_afetado",
            "prioridade", "indice_ahp", "analise_ia_status",
            "tempo_espera_minutos", "sla", "status_atendimento", "criado_em",
        ]

    def get_tempo_espera_minutos(self, obj):
        return WaitingTimeService.compute_wait_minutes(obj)

    def get_sla(self, obj):
        return None


class EncaminharChamadoInputSerializer(serializers.Serializer):
    motivo = serializers.CharField(allow_blank=False)


class AtendimentoPublicoCreateSerializer(serializers.ModelSerializer):
    """
    Criacao anonima de atendimento (chat publico). `origem` e sempre forcado
    para CHAT no servidor -- nunca aceito do cliente. `mensagem_inicial`
    (write-only) cria a primeira MensagemAtendimento na mesma chamada.
    """

    mensagem_inicial = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Atendimento
        fields = [
            "id", "session_token", "nome", "email", "telefone", "status_atendimento",
            "analise_ia_status", "criado_em", "mensagem_inicial",
        ]
        read_only_fields = ["id", "session_token", "status_atendimento", "analise_ia_status", "criado_em"]

    def create(self, validated_data):
        validated_data.pop("mensagem_inicial", None)
        return Atendimento.objects.create(**validated_data)


class AtendimentoFilaSerializer(serializers.ModelSerializer):
    """Card da fila (secao 27) -- `sla` e sempre None, fora de escopo nesta fase."""

    tempo_espera_minutos = serializers.SerializerMethodField()
    sla = serializers.SerializerMethodField()
    dados_ausentes = serializers.SerializerMethodField()
    anexos_count = serializers.SerializerMethodField()
    atendente = serializers.SerializerMethodField()

    class Meta:
        model = Atendimento
        fields = [
            "id", "nome", "cliente", "assunto", "resumo", "servico_afetado",
            "prioridade", "indice_ahp", "analise_ia_status",
            "tempo_espera_minutos", "sla", "atendente", "anexos_count",
            "dados_ausentes", "regra_critica_confirmada",
            "status_atendimento", "criado_em",
        ]

    def get_tempo_espera_minutos(self, obj):
        return WaitingTimeService.compute_wait_minutes(obj)

    def get_sla(self, obj):
        return None

    def get_dados_ausentes(self, obj):
        return obj.avaliacoes.filter(dados_ausentes=True).exists()

    def get_anexos_count(self, obj):
        return obj.anexos.count()

    def get_atendente(self, obj):
        if not obj.atendente_id:
            return None
        return {"id": obj.atendente_id, "name": obj.atendente.name}
