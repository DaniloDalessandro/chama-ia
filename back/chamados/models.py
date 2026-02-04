from django.db import models
from django.conf import settings
import uuid


class Chamado(models.Model):
    """
    Model principal para armazenar chamados/tickets abertos via Landing Page.
    Inclui campos de auditoria e preparado para integracao com chat/IA.
    """

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

    # Dados do chamado
    tipo = models.CharField(
        max_length=50,
        choices=TipoSolicitacao.choices,
        default=TipoSolicitacao.OUTROS,
        verbose_name="Tipo de Solicitacao"
    )
    assunto = models.CharField(max_length=255, verbose_name="Assunto")
    descricao = models.TextField(verbose_name="Descricao")

    # Status e prioridade
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

    # Campos para integracao futura
    chat_session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID Sessao Chat"
    )
    ia_processed = models.BooleanField(default=False, verbose_name="Processado por IA")
    ia_response = models.TextField(blank=True, verbose_name="Resposta IA")

    class Meta:
        verbose_name = "Chamado"
        verbose_name_plural = "Chamados"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["protocolo"]),
            models.Index(fields=["email"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"#{self.protocolo} - {self.assunto}"

    def save(self, *args, **kwargs):
        if not self.protocolo:
            self.protocolo = self._generate_protocolo()
        super().save(*args, **kwargs)

    def _generate_protocolo(self):
        """Gera um protocolo unico no formato: YYYYMMDD-XXXXX"""
        from django.utils import timezone
        import random
        import string

        date_part = timezone.now().strftime("%Y%m%d")
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"{date_part}-{random_part}"


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
        verbose_name="Arquivo"
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
