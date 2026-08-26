from rest_framework import serializers

from .models import Comparacao, Criterio, FaixaTempoEspera, Intensidade, Termo, VersaoAHP

_AUDIT_READ_ONLY = ("criado_em", "criado_por", "atualizado_em", "atualizado_por")


class CriterioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Criterio
        fields = [
            "id", "nome", "codigo", "descricao", "orientacao", "ordem", "ativo",
            "importancia_negocio", "regra_critica", "exige_revisao_humana",
            "permite_deteccao_semantica", "orientacoes_para_ia", "exemplos_positivos",
            "exemplos_negativos", "cor_identificacao", "icone",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
            "excluido_em", "excluido_por",
        ]
        read_only_fields = _AUDIT_READ_ONLY + ("excluido_em", "excluido_por")


class IntensidadeSerializer(serializers.ModelSerializer):
    codigo_display = serializers.CharField(source="get_codigo_display", read_only=True)

    class Meta:
        model = Intensidade
        fields = [
            "id", "criterio", "nome", "codigo", "codigo_display", "descricao", "ordem",
            "orientacoes_para_ia", "exemplo_positivo", "exemplo_negativo", "ativo",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
            "excluido_em", "excluido_por",
        ]
        read_only_fields = _AUDIT_READ_ONLY + ("excluido_em", "excluido_por")


class TermoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Termo
        fields = [
            "id", "criterio", "termo", "descricao", "tipo_correspondencia", "intensidade_base",
            "exige_contexto", "regra_critica", "considerar_mensagem_atual", "considerar_historico",
            "considerar_anexos", "considerar_imagens", "status_aprovacao", "ativo",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
            "excluido_em", "excluido_por",
        ]
        read_only_fields = _AUDIT_READ_ONLY + ("excluido_em", "excluido_por")

    def validate(self, attrs):
        criterio = attrs.get("criterio") or getattr(self.instance, "criterio", None)
        intensidade_base = attrs.get("intensidade_base") or getattr(self.instance, "intensidade_base", None)
        if criterio and intensidade_base and intensidade_base.criterio_id != criterio.id:
            raise serializers.ValidationError(
                "A intensidade base precisa pertencer ao mesmo criterio do termo."
            )
        return attrs


class FaixaTempoEsperaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FaixaTempoEspera
        fields = [
            "id", "criterio", "minutos_min", "minutos_max", "intensidade", "ordem", "ativo",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]
        read_only_fields = _AUDIT_READ_ONLY

    def validate(self, attrs):
        minutos_min = attrs.get("minutos_min", getattr(self.instance, "minutos_min", None))
        minutos_max = attrs.get("minutos_max", getattr(self.instance, "minutos_max", None))
        if minutos_max is not None and minutos_max <= minutos_min:
            raise serializers.ValidationError("minutos_max precisa ser maior que minutos_min.")

        criterio = attrs.get("criterio") or getattr(self.instance, "criterio", None)
        intensidade = attrs.get("intensidade") or getattr(self.instance, "intensidade", None)
        if criterio and intensidade and intensidade.criterio_id != criterio.id:
            raise serializers.ValidationError("A intensidade precisa pertencer ao mesmo criterio da faixa.")
        return attrs


class ComparacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comparacao
        fields = [
            "id", "versao_ahp", "tipo", "criterio_contexto", "criterio_linha", "criterio_coluna",
            "intensidade_linha", "intensidade_coluna", "valor_saaty",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]
        read_only_fields = _AUDIT_READ_ONLY


class VersaoAHPSerializer(serializers.ModelSerializer):
    class Meta:
        model = VersaoAHP
        fields = [
            "id", "numero_versao", "estado", "descricao",
            "pesos_criterios", "lambda_max_criterios", "ci_criterios", "cr_criterios",
            "prioridades_intensidades", "lambda_max_intensidades", "ci_intensidades", "cr_intensidades",
            "p_max", "ativada_em", "ativada_por", "arquivada_em", "mensagens_erro",
            "criado_em", "criado_por", "atualizado_em", "atualizado_por",
        ]
        read_only_fields = [f for f in fields if f not in ("descricao",)]  # so descricao e editavel via API


class ComparacaoItemInputSerializer(serializers.Serializer):
    """Um item de submissao em lote: id do item na linha, id do item na coluna, valor de Saaty."""

    item_linha_id = serializers.IntegerField()
    item_coluna_id = serializers.IntegerField()
    valor_saaty = serializers.FloatField()
