from rest_framework import serializers
from django.utils import timezone
from django.utils.html import strip_tags
import bleach

from .models import Chamado, AnexoChamado, HistoricoChamado, ComentarioChamado


# ============================================
# Funcoes de sanitizacao
# ============================================

def sanitize_text(text: str) -> str:
    """Remove tags HTML e sanitiza o texto."""
    if not text:
        return text
    # Remove tags HTML
    cleaned = strip_tags(text)
    # Remove caracteres perigosos
    cleaned = bleach.clean(cleaned, tags=[], strip=True)
    return cleaned.strip()


# ============================================
# Serializers de Anexos
# ============================================

class AnexoChamadoSerializer(serializers.ModelSerializer):
    """Serializer para leitura de anexos."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = AnexoChamado
        fields = [
            "id",
            "nome_original",
            "tipo",
            "tamanho",
            "mime_type",
            "url",
            "created_at",
        ]
        read_only_fields = fields

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.arquivo and request:
            return request.build_absolute_uri(obj.arquivo.url)
        return None


class AnexoUploadSerializer(serializers.Serializer):
    """Serializer para upload de anexos."""

    arquivo = serializers.FileField()

    ALLOWED_MIME_TYPES = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
    ]
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

    def validate_arquivo(self, value):
        # Validar tipo
        if value.content_type not in self.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                "Tipo de arquivo nao permitido. Use PDF, JPG, PNG ou WebP."
            )

        # Validar tamanho
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                "Arquivo muito grande. Tamanho maximo: 5MB."
            )

        return value


# ============================================
# Serializers de Historico
# ============================================

class HistoricoChamadoSerializer(serializers.ModelSerializer):
    """Serializer para leitura do historico."""

    tipo_acao_display = serializers.CharField(source="get_tipo_acao_display", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.name", read_only=True, default=None)

    class Meta:
        model = HistoricoChamado
        fields = [
            "id",
            "tipo_acao",
            "tipo_acao_display",
            "descricao",
            "valor_anterior",
            "valor_novo",
            "usuario_nome",
            "created_at",
        ]
        read_only_fields = fields


# ============================================
# Serializers de Comentarios
# ============================================

class ComentarioChamadoSerializer(serializers.ModelSerializer):
    """Serializer para leitura de comentarios."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = ComentarioChamado
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "conteudo",
            "autor_nome",
            "is_from_client",
            "created_at",
        ]
        read_only_fields = fields


class ComentarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para criacao de comentarios."""

    class Meta:
        model = ComentarioChamado
        fields = ["tipo", "conteudo"]

    def validate_conteudo(self, value):
        return sanitize_text(value)


# ============================================
# Serializers de Chamado - Criacao Publica
# ============================================

class ChamadoPublicoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criacao de chamados via Landing Page (publico).
    Campos minimos e sanitizacao de dados.
    """

    anexos = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        max_length=5,
        write_only=True
    )

    class Meta:
        model = Chamado
        fields = [
            "nome",
            "email",
            "telefone",
            "tipo",
            "assunto",
            "descricao",
            "anexos",
        ]

    def validate_nome(self, value):
        value = sanitize_text(value)
        if len(value) < 3:
            raise serializers.ValidationError("Nome deve ter pelo menos 3 caracteres.")
        if len(value) > 255:
            raise serializers.ValidationError("Nome muito longo.")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        return value

    def validate_assunto(self, value):
        value = sanitize_text(value)
        if len(value) < 5:
            raise serializers.ValidationError("Assunto deve ter pelo menos 5 caracteres.")
        if len(value) > 255:
            raise serializers.ValidationError("Assunto muito longo.")
        return value

    def validate_descricao(self, value):
        value = sanitize_text(value)
        if len(value) < 20:
            raise serializers.ValidationError("Descricao deve ter pelo menos 20 caracteres.")
        if len(value) > 5000:
            raise serializers.ValidationError("Descricao muito longa (max 5000 caracteres).")
        return value

    def validate_anexos(self, value):
        if not value:
            return value

        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/webp"]
        max_size = 5 * 1024 * 1024  # 5MB

        for arquivo in value:
            if arquivo.content_type not in allowed_types:
                raise serializers.ValidationError(
                    f"Tipo de arquivo nao permitido: {arquivo.name}"
                )
            if arquivo.size > max_size:
                raise serializers.ValidationError(
                    f"Arquivo muito grande: {arquivo.name} (max 5MB)"
                )

        return value

    def create(self, validated_data):
        anexos_data = validated_data.pop("anexos", [])
        request = self.context.get("request")

        # Adicionar dados de rastreamento
        if request:
            validated_data["ip_address"] = self._get_client_ip(request)
            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:500]
            validated_data["origem"] = Chamado.Origem.LANDING_PAGE

        # Criar chamado
        chamado = Chamado.objects.create(**validated_data)

        # Criar anexos
        for arquivo in anexos_data:
            tipo = self._get_tipo_arquivo(arquivo.content_type)
            AnexoChamado.objects.create(
                chamado=chamado,
                arquivo=arquivo,
                nome_original=arquivo.name,
                tipo=tipo,
                tamanho=arquivo.size,
                mime_type=arquivo.content_type,
            )

        # Registrar no historico
        HistoricoChamado.objects.create(
            chamado=chamado,
            tipo_acao=HistoricoChamado.TipoAcao.CRIADO,
            descricao=f"Chamado criado via Landing Page por {chamado.nome}",
            ip_address=validated_data.get("ip_address"),
        )

        return chamado

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _get_tipo_arquivo(self, mime_type):
        if mime_type == "application/pdf":
            return AnexoChamado.TipoArquivo.PDF
        elif mime_type.startswith("image/"):
            return AnexoChamado.TipoArquivo.IMAGEM
        return AnexoChamado.TipoArquivo.OUTRO


class ChamadoPublicoResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta apos criar chamado (dados minimos)."""

    class Meta:
        model = Chamado
        fields = [
            "protocolo",
            "status",
            "created_at",
        ]
        read_only_fields = fields


# ============================================
# Serializers de Chamado - Administrativo
# ============================================

class ChamadoListSerializer(serializers.ModelSerializer):
    """Serializer para listagem de chamados (admin)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prioridade_display = serializers.CharField(source="get_prioridade_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    origem_display = serializers.CharField(source="get_origem_display", read_only=True)
    atendente_nome = serializers.CharField(source="atendente.name", read_only=True, default=None)
    total_anexos = serializers.SerializerMethodField()
    total_comentarios = serializers.SerializerMethodField()

    class Meta:
        model = Chamado
        fields = [
            "id",
            "protocolo",
            "nome",
            "email",
            "tipo",
            "tipo_display",
            "assunto",
            "status",
            "status_display",
            "prioridade",
            "prioridade_display",
            "origem",
            "origem_display",
            "atendente_nome",
            "total_anexos",
            "total_comentarios",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_total_anexos(self, obj):
        return obj.anexos.count()

    def get_total_comentarios(self, obj):
        return obj.comentarios.count()


class ChamadoDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalhes completos do chamado (admin)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prioridade_display = serializers.CharField(source="get_prioridade_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    origem_display = serializers.CharField(source="get_origem_display", read_only=True)
    atendente_nome = serializers.CharField(source="atendente.name", read_only=True, default=None)
    usuario_nome = serializers.CharField(source="usuario.name", read_only=True, default=None)
    anexos = AnexoChamadoSerializer(many=True, read_only=True)
    historico = HistoricoChamadoSerializer(many=True, read_only=True)
    comentarios = ComentarioChamadoSerializer(many=True, read_only=True)

    class Meta:
        model = Chamado
        fields = [
            "id",
            "protocolo",
            "nome",
            "email",
            "telefone",
            "tipo",
            "tipo_display",
            "assunto",
            "descricao",
            "status",
            "status_display",
            "prioridade",
            "prioridade_display",
            "origem",
            "origem_display",
            "ip_address",
            "user_agent",
            "usuario_nome",
            "atendente_nome",
            "chat_session_id",
            "ia_processed",
            "ia_response",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
            "anexos",
            "historico",
            "comentarios",
        ]
        read_only_fields = fields


class ChamadoUpdateStatusSerializer(serializers.ModelSerializer):
    """Serializer para atualizacao de status do chamado."""

    class Meta:
        model = Chamado
        fields = ["status"]

    def validate_status(self, value):
        instance = self.instance
        if not instance:
            return value

        # Validar transicoes de status
        current_status = instance.status
        allowed_transitions = {
            Chamado.Status.ABERTO: [
                Chamado.Status.EM_ANALISE,
                Chamado.Status.EM_ATENDIMENTO,
                Chamado.Status.CANCELADO,
            ],
            Chamado.Status.EM_ANALISE: [
                Chamado.Status.EM_ATENDIMENTO,
                Chamado.Status.AGUARDANDO_CLIENTE,
                Chamado.Status.RESOLVIDO,
                Chamado.Status.CANCELADO,
            ],
            Chamado.Status.EM_ATENDIMENTO: [
                Chamado.Status.AGUARDANDO_CLIENTE,
                Chamado.Status.RESOLVIDO,
                Chamado.Status.CANCELADO,
            ],
            Chamado.Status.AGUARDANDO_CLIENTE: [
                Chamado.Status.EM_ATENDIMENTO,
                Chamado.Status.RESOLVIDO,
                Chamado.Status.CANCELADO,
            ],
            Chamado.Status.RESOLVIDO: [
                Chamado.Status.FECHADO,
                Chamado.Status.EM_ATENDIMENTO,  # Reabrir
            ],
            Chamado.Status.FECHADO: [],  # Nao pode alterar
            Chamado.Status.CANCELADO: [],  # Nao pode alterar
        }

        if value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Nao e possivel alterar de '{instance.get_status_display()}' para '{dict(Chamado.Status.choices).get(value)}'."
            )

        return value

    def update(self, instance, validated_data):
        old_status = instance.status
        new_status = validated_data.get("status", old_status)

        if old_status != new_status:
            instance.status = new_status

            # Atualizar timestamps
            if new_status == Chamado.Status.RESOLVIDO:
                instance.resolved_at = timezone.now()
            elif new_status == Chamado.Status.FECHADO:
                instance.closed_at = timezone.now()

            instance.save()

            # Registrar no historico
            request = self.context.get("request")
            HistoricoChamado.objects.create(
                chamado=instance,
                tipo_acao=HistoricoChamado.TipoAcao.STATUS_ALTERADO,
                descricao=f"Status alterado de {dict(Chamado.Status.choices).get(old_status)} para {dict(Chamado.Status.choices).get(new_status)}",
                valor_anterior=old_status,
                valor_novo=new_status,
                usuario=request.user if request and request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request) if request else None,
            )

        return instance

    def _get_client_ip(self, request):
        if not request:
            return None
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class ChamadoAtribuirAtendenteSerializer(serializers.ModelSerializer):
    """Serializer para atribuir atendente ao chamado."""

    class Meta:
        model = Chamado
        fields = ["atendente"]

    def update(self, instance, validated_data):
        old_atendente = instance.atendente
        new_atendente = validated_data.get("atendente")

        if old_atendente != new_atendente:
            instance.atendente = new_atendente
            instance.save()

            # Registrar no historico
            request = self.context.get("request")
            HistoricoChamado.objects.create(
                chamado=instance,
                tipo_acao=HistoricoChamado.TipoAcao.ATENDENTE_ATRIBUIDO,
                descricao=f"Atendente atribuido: {new_atendente.name if new_atendente else 'Removido'}",
                valor_anterior=old_atendente.name if old_atendente else "",
                valor_novo=new_atendente.name if new_atendente else "",
                usuario=request.user if request and request.user.is_authenticated else None,
            )

        return instance


class ChamadoUpdatePrioridadeSerializer(serializers.ModelSerializer):
    """Serializer para atualizar prioridade do chamado."""

    class Meta:
        model = Chamado
        fields = ["prioridade"]

    def update(self, instance, validated_data):
        old_prioridade = instance.prioridade
        new_prioridade = validated_data.get("prioridade", old_prioridade)

        if old_prioridade != new_prioridade:
            instance.prioridade = new_prioridade
            instance.save()

            # Registrar no historico
            request = self.context.get("request")
            HistoricoChamado.objects.create(
                chamado=instance,
                tipo_acao=HistoricoChamado.TipoAcao.PRIORIDADE_ALTERADA,
                descricao=f"Prioridade alterada de {dict(Chamado.Prioridade.choices).get(old_prioridade)} para {dict(Chamado.Prioridade.choices).get(new_prioridade)}",
                valor_anterior=old_prioridade,
                valor_novo=new_prioridade,
                usuario=request.user if request and request.user.is_authenticated else None,
            )

        return instance


# ============================================
# Serializer para consulta publica por protocolo
# ============================================

class ChamadoConsultaPublicaSerializer(serializers.ModelSerializer):
    """Serializer para consulta publica do chamado (dados limitados)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    comentarios_publicos = serializers.SerializerMethodField()

    class Meta:
        model = Chamado
        fields = [
            "protocolo",
            "assunto",
            "status",
            "status_display",
            "created_at",
            "updated_at",
            "resolved_at",
            "comentarios_publicos",
        ]
        read_only_fields = fields

    def get_comentarios_publicos(self, obj):
        comentarios = obj.comentarios.filter(tipo=ComentarioChamado.TipoComentario.PUBLICO)
        return ComentarioChamadoSerializer(comentarios, many=True).data
