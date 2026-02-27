from django.db import models
from django.conf import settings
import uuid
from .validators import FileValidator
from cryptography.fernet import Fernet


class Chamado(models.Model):
    """
    Model principal para armazenar chamados/tickets abertos via Landing Page.
    Inclui campos de auditoria e preparado para integracao com chat/IA.
    """

    # Status para fluxo Kanban
    class StatusKanban(models.TextChoices):
        NOVO = "novo", "Novo"
        EM_ANDAMENTO = "em_andamento", "Em Andamento"
        CONCLUIDO = "concluido", "Concluido"

    # Status detalhado (compatibilidade)
    class Status(models.TextChoices):
        ABERTO = "aberto", "Aberto"
        EM_ANALISE = "em_analise", "Em Analise"
        EM_ATENDIMENTO = "em_atendimento", "Em Atendimento"
        AGUARDANDO_CLIENTE = "aguardando_cliente", "Aguardando Cliente"
        RESOLVIDO = "resolvido", "Resolvido"
        FECHADO = "fechado", "Fechado"
        CANCELADO = "cancelado", "Cancelado"

    class Prioridade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Media"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class TipoSolicitacao(models.TextChoices):
        NOTA_FISCAL = "nota-fiscal", "Nota Fiscal"
        ERRO_SISTEMA = "erro-sistema", "Erro no Sistema"
        FINANCEIRO = "financeiro", "Financeiro"
        OUTROS = "outros", "Outros"

    class Origem(models.TextChoices):
        LANDING_PAGE = "landing_page", "Landing Page"
        CHAT = "chat", "Chat"
        EMAIL = "email", "E-mail"
        TELEFONE = "telefone", "Telefone"
        DASHBOARD = "dashboard", "Dashboard"

    # Identificador unico publico
    protocolo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Protocolo"
    )

    # Dados do solicitante
    nome = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(verbose_name="E-mail")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados",
        verbose_name="Cliente/Empresa"
    )

    # Dados do chamado
    tipo = models.CharField(
        max_length=50,
        choices=TipoSolicitacao.choices,
        default=TipoSolicitacao.OUTROS,
        verbose_name="Tipo de Solicitacao"
    )
    assunto = models.CharField(max_length=255, verbose_name="Assunto")
    descricao = models.TextField(verbose_name="Descricao")

    # Status Kanban (para visualizacao em quadro)
    status_kanban = models.CharField(
        max_length=20,
        choices=StatusKanban.choices,
        default=StatusKanban.NOVO,
        verbose_name="Status Kanban"
    )

    # Status detalhado
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ABERTO,
        verbose_name="Status"
    )
    prioridade = models.CharField(
        max_length=20,
        choices=Prioridade.choices,
        default=Prioridade.MEDIA,
        verbose_name="Prioridade"
    )

    # Origem e rastreamento
    origem = models.CharField(
        max_length=30,
        choices=Origem.choices,
        default=Origem.LANDING_PAGE,
        verbose_name="Origem"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereco IP"
    )
    user_agent = models.TextField(blank=True, verbose_name="User Agent")

    # Relacionamentos (preparado para integracao)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_abertos",
        verbose_name="Usuario"
    )
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_atendidos",
        verbose_name="Atendente"
    )

    # Campos de auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Resolvido em")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fechado em")

    # Auditoria de usuario (quem criou/atualizou)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_criados",
        verbose_name="Criado por"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chamados_atualizados",
        verbose_name="Atualizado por"
    )

    # Campos para integracao futura
    chat_session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID Sessao Chat"
    )
    ia_processed = models.BooleanField(default=False, verbose_name="Processado por IA")
    ia_response = models.TextField(blank=True, verbose_name="Resposta IA")

    # Campos de classificacao IA
    ia_categoria = models.CharField(max_length=30, blank=True, verbose_name="Categoria IA")
    ia_prioridade_sugerida = models.CharField(max_length=20, blank=True, verbose_name="Prioridade Sugerida IA")
    ia_resumo = models.TextField(blank=True, verbose_name="Resumo IA")
    ia_problema_principal = models.TextField(blank=True, verbose_name="Problema Principal IA")
    ia_palavras_chave = models.JSONField(default=list, blank=True, verbose_name="Palavras-chave IA")
    ia_confianca = models.FloatField(default=0.0, verbose_name="Confianca IA")
    ia_processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Processado IA em")

    # Deteccao de recorrencia
    is_recorrente = models.BooleanField(default=False, verbose_name="Chamado Recorrente")
    chamado_similar_ref = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chamados_similares",
        verbose_name="Chamado Similar"
    )
    similaridade_score = models.FloatField(null=True, blank=True, verbose_name="Score de Similaridade")

    class Meta:
        verbose_name = "Chamado"
        verbose_name_plural = "Chamados"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["protocolo"]),
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
            models.Index(fields=["status_kanban"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"#{self.protocolo} - {self.assunto}"

    def save(self, *args, **kwargs):
        if not self.protocolo:
            from django.db import IntegrityError
            for attempt in range(5):
                self.protocolo = self._generate_protocolo()
                self._sync_status_kanban()
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    if attempt == 4:
                        raise
                    self.protocolo = ""
                    continue

        # Sincronizar status_kanban com status detalhado
        self._sync_status_kanban()

        super().save(*args, **kwargs)

    def _sync_status_kanban(self):
        """Sincroniza o status_kanban baseado no status detalhado."""
        status_map = {
            self.Status.ABERTO: self.StatusKanban.NOVO,
            self.Status.EM_ANALISE: self.StatusKanban.EM_ANDAMENTO,
            self.Status.EM_ATENDIMENTO: self.StatusKanban.EM_ANDAMENTO,
            self.Status.AGUARDANDO_CLIENTE: self.StatusKanban.EM_ANDAMENTO,
            self.Status.RESOLVIDO: self.StatusKanban.CONCLUIDO,
            self.Status.FECHADO: self.StatusKanban.CONCLUIDO,
            self.Status.CANCELADO: self.StatusKanban.CONCLUIDO,
        }
        self.status_kanban = status_map.get(self.status, self.StatusKanban.NOVO)

    def update_status_from_kanban(self, new_kanban_status, user=None):
        """
        Atualiza o status detalhado baseado na mudanca do Kanban.
        Usado quando o usuario arrasta o card no Kanban.
        """
        old_kanban = self.status_kanban
        self.status_kanban = new_kanban_status

        # Mapear para status detalhado
        if new_kanban_status == self.StatusKanban.NOVO:
            self.status = self.Status.ABERTO
        elif new_kanban_status == self.StatusKanban.EM_ANDAMENTO:
            self.status = self.Status.EM_ATENDIMENTO
        elif new_kanban_status == self.StatusKanban.CONCLUIDO:
            self.status = self.Status.RESOLVIDO
            from django.utils import timezone
            self.resolved_at = timezone.now()

        # Atualizar auditoria
        if user and user.is_authenticated:
            self.updated_by = user

        self.save()
        return old_kanban != new_kanban_status

    def _generate_protocolo(self):
        """Gera um protocolo sequencial no formato: XXXX/YYYY (ex: 0001/2026)"""
        from django.utils import timezone
        from django.db.models import Max

        ano_atual = str(timezone.now().year)
        sufixo = f"/{ano_atual}"

        ultimo = (
            Chamado.objects.filter(protocolo__endswith=sufixo)
            .aggregate(max_proto=Max("protocolo"))
            .get("max_proto")
        )

        if ultimo:
            try:
                seq = int(ultimo.split("/")[0]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1

        return f"{seq:04d}/{ano_atual}"


class AnexoChamado(models.Model):
    """
    Model para armazenar anexos de chamados (PDFs, imagens, etc).
    """

    class TipoArquivo(models.TextChoices):
        PDF = "pdf", "PDF"
        IMAGEM = "imagem", "Imagem"
        DOCUMENTO = "documento", "Documento"
        OUTRO = "outro", "Outro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="anexos",
        verbose_name="Chamado"
    )
    arquivo = models.FileField(
        upload_to="chamados/anexos/%Y/%m/",
        verbose_name="Arquivo",
        validators=[FileValidator()]
    )
    nome_original = models.CharField(max_length=255, verbose_name="Nome Original")
    tipo = models.CharField(
        max_length=20,
        choices=TipoArquivo.choices,
        default=TipoArquivo.OUTRO,
        verbose_name="Tipo"
    )
    tamanho = models.PositiveIntegerField(verbose_name="Tamanho (bytes)")
    mime_type = models.CharField(max_length=100, verbose_name="MIME Type")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.nome_original} ({self.chamado.protocolo})"


class HistoricoChamado(models.Model):
    """
    Model para registrar historico de alteracoes nos chamados (auditoria).
    """

    class TipoAcao(models.TextChoices):
        CRIADO = "criado", "Chamado Criado"
        STATUS_ALTERADO = "status_alterado", "Status Alterado"
        ATENDENTE_ATRIBUIDO = "atendente_atribuido", "Atendente Atribuido"
        COMENTARIO = "comentario", "Comentario Adicionado"
        ANEXO_ADICIONADO = "anexo_adicionado", "Anexo Adicionado"
        PRIORIDADE_ALTERADA = "prioridade_alterada", "Prioridade Alterada"
        RESPOSTA_IA = "resposta_ia", "Resposta IA"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="historico",
        verbose_name="Chamado"
    )
    tipo_acao = models.CharField(
        max_length=30,
        choices=TipoAcao.choices,
        verbose_name="Tipo de Acao"
    )
    descricao = models.TextField(verbose_name="Descricao")
    valor_anterior = models.CharField(max_length=255, blank=True, verbose_name="Valor Anterior")
    valor_novo = models.CharField(max_length=255, blank=True, verbose_name="Valor Novo")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Historico"
        verbose_name_plural = "Historicos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.chamado.protocolo} - {self.get_tipo_acao_display()}"


class EmbeddingChamado(models.Model):
    """
    Model para armazenar embeddings de chamados para deteccao de similaridade.
    """

    chamado = models.OneToOneField(
        Chamado,
        on_delete=models.CASCADE,
        related_name="embedding",
        verbose_name="Chamado"
    )
    embedding_vector = models.JSONField(verbose_name="Vetor de Embedding")
    texto_base = models.TextField(verbose_name="Texto Base")
    texto_hash = models.CharField(max_length=64, db_index=True, verbose_name="Hash do Texto")
    modelo = models.CharField(max_length=50, verbose_name="Modelo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Embedding Chamado"
        verbose_name_plural = "Embeddings Chamados"

    def __str__(self):
        return f"Embedding de {self.chamado.protocolo}"


class EmbeddingCache(models.Model):
    """
    Cache global de embeddings para evitar reprocessar textos identicos.
    Textos iguais geram o mesmo embedding, entao podemos reutilizar.
    """

    texto_hash = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="Hash do Texto")
    embedding_vector = models.JSONField(verbose_name="Vetor de Embedding")
    modelo = models.CharField(max_length=50, verbose_name="Modelo")
    uso_count = models.PositiveIntegerField(default=1, verbose_name="Vezes Utilizado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    last_used_at = models.DateTimeField(auto_now=True, verbose_name="Ultimo Uso")

    class Meta:
        verbose_name = "Cache de Embedding"
        verbose_name_plural = "Cache de Embeddings"

    def __str__(self):
        return f"Cache {self.texto_hash[:8]}... (usado {self.uso_count}x)"


class ComentarioChamado(models.Model):
    """
    Model para comentarios/interacoes no chamado.
    """

    class TipoComentario(models.TextChoices):
        INTERNO = "interno", "Interno (apenas equipe)"
        PUBLICO = "publico", "Publico (visivel ao cliente)"
        AUTOMATICO = "automatico", "Automatico (sistema/IA)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="comentarios",
        verbose_name="Chamado"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoComentario.choices,
        default=TipoComentario.PUBLICO,
        verbose_name="Tipo"
    )
    conteudo = models.TextField(verbose_name="Conteudo")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Autor"
    )
    autor_nome = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nome do Autor"
    )
    is_from_client = models.BooleanField(default=False, verbose_name="Do Cliente")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Comentario"
        verbose_name_plural = "Comentarios"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comentario em {self.chamado.protocolo}"


class Notification(models.Model):
    """
    Model para notificacoes em tempo real para usuarios internos.
    """

    class NotificationType(models.TextChoices):
        CHAMADO_CREATED = "chamado_created", "Novo Chamado"
        CHAMADO_ASSIGNED = "chamado_assigned", "Chamado Atribuido"
        PRIORITY_URGENT = "priority_urgent", "Prioridade Urgente"
        STATUS_CHANGED = "status_changed", "Status Alterado"
        NEW_COMMENT = "new_comment", "Novo Comentario"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Usuario"
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name="Tipo"
    )
    title = models.CharField(max_length=255, verbose_name="Titulo")
    message = models.TextField(verbose_name="Mensagem")
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="Chamado"
    )
    is_read = models.BooleanField(default=False, verbose_name="Lida")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lida em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    class Meta:
        verbose_name = "Notificacao"
        verbose_name_plural = "Notificacoes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        """Marca a notificacao como lida."""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class WebhookConfig(models.Model):
    """
    Model para configuracao de webhooks HTTP customizaveis.
    Suporta Discord, Slack e webhooks personalizados.
    """

    class WebhookType(models.TextChoices):
        DISCORD = "discord", "Discord"
        SLACK = "slack", "Slack"
        CUSTOM = "custom", "Custom HTTP"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome")
    webhook_type = models.CharField(
        max_length=20,
        choices=WebhookType.choices,
        default=WebhookType.CUSTOM,
        verbose_name="Tipo"
    )
    encrypted_url = models.TextField(verbose_name="URL Criptografada")
    trigger_events = models.JSONField(
        default=list,
        verbose_name="Eventos Gatilho",
        help_text="Lista de eventos que disparam o webhook: chamado_created, chamado_assigned, priority_urgent"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    max_retries = models.PositiveSmallIntegerField(default=3, verbose_name="Max Tentativas")

    # Statistics
    total_sent = models.PositiveIntegerField(default=0, verbose_name="Total Enviados")
    total_success = models.PositiveIntegerField(default=0, verbose_name="Total Sucesso")
    total_failed = models.PositiveIntegerField(default=0, verbose_name="Total Falhas")
    last_triggered_at = models.DateTimeField(null=True, blank=True, verbose_name="Ultimo Disparo")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Configuracao de Webhook"
        verbose_name_plural = "Configuracoes de Webhooks"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_webhook_type_display()})"

    def set_url(self, url):
        """Criptografa e armazena a URL do webhook."""
        if not settings.WEBHOOK_ENCRYPTION_KEY:
            raise ValueError("WEBHOOK_ENCRYPTION_KEY not configured in settings")

        fernet = Fernet(settings.WEBHOOK_ENCRYPTION_KEY.encode())
        self.encrypted_url = fernet.encrypt(url.encode()).decode()

    def get_url(self):
        """Descriptografa e retorna a URL do webhook."""
        if not settings.WEBHOOK_ENCRYPTION_KEY:
            raise ValueError("WEBHOOK_ENCRYPTION_KEY not configured in settings")

        fernet = Fernet(settings.WEBHOOK_ENCRYPTION_KEY.encode())
        return fernet.decrypt(self.encrypted_url.encode()).decode()

    def increment_stats(self, success=True):
        """Incrementa estatisticas de uso."""
        from django.utils import timezone
        self.total_sent += 1
        if success:
            self.total_success += 1
        else:
            self.total_failed += 1
        self.last_triggered_at = timezone.now()
        self.save(update_fields=["total_sent", "total_success", "total_failed", "last_triggered_at"])


class WebhookLog(models.Model):
    """
    Model para audit log de entregas de webhooks.
    """

    class Status(models.TextChoices):
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Falha"
        RETRYING = "retrying", "Tentando Novamente"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook = models.ForeignKey(
        WebhookConfig,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="Webhook"
    )
    chamado = models.ForeignKey(
        Chamado,
        on_delete=models.CASCADE,
        related_name="webhook_logs",
        null=True,
        blank=True,
        verbose_name="Chamado"
    )
    event = models.CharField(max_length=50, verbose_name="Evento")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        verbose_name="Status"
    )
    payload_sent = models.JSONField(verbose_name="Payload Enviado")
    response_status_code = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="HTTP Status")
    response_body = models.TextField(blank=True, verbose_name="Resposta")
    error_message = models.TextField(blank=True, verbose_name="Mensagem de Erro")
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name="Tentativas")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Log de Webhook"
        verbose_name_plural = "Logs de Webhooks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.webhook.name} - {self.event} - {self.status}"
