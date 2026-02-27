from django.contrib import admin
from .models import (
    Chamado,
    AnexoChamado,
    HistoricoChamado,
    ComentarioChamado,
    EmbeddingChamado,
    EmbeddingCache,
    Notification,
    WebhookConfig,
    WebhookLog,
)


class AnexoChamadoInline(admin.TabularInline):
    model = AnexoChamado
    extra = 0
    readonly_fields = ["id", "nome_original", "tipo", "tamanho", "mime_type", "created_at"]


class HistoricoChamadoInline(admin.TabularInline):
    model = HistoricoChamado
    extra = 0
    readonly_fields = ["id", "tipo_acao", "descricao", "valor_anterior", "valor_novo", "usuario", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ComentarioChamadoInline(admin.TabularInline):
    model = ComentarioChamado
    extra = 0
    readonly_fields = ["id", "created_at"]


@admin.register(Chamado)
class ChamadoAdmin(admin.ModelAdmin):
    list_display = [
        "protocolo",
        "nome",
        "email",
        "cliente",
        "tipo",
        "assunto",
        "status",
        "status_kanban",
        "prioridade",
        "ia_processed",
        "is_recorrente",
        "atendente",
        "created_at",
    ]
    list_filter = ["status", "status_kanban", "prioridade", "tipo", "origem", "ia_processed", "is_recorrente", "cliente", "created_at"]
    search_fields = ["protocolo", "nome", "email", "assunto", "descricao", "cliente__nome", "cliente__nome_fantasia"]
    readonly_fields = [
        "protocolo",
        "ip_address",
        "user_agent",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
        "created_by",
        "updated_by",
        # Campos IA (somente leitura)
        "ia_categoria",
        "ia_prioridade_sugerida",
        "ia_resumo",
        "ia_problema_principal",
        "ia_palavras_chave",
        "ia_confianca",
        "ia_processed_at",
        "similaridade_score",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        ("Identificacao", {
            "fields": ("protocolo", "origem")
        }),
        ("Solicitante", {
            "fields": ("nome", "email", "telefone", "usuario")
        }),
        ("Chamado", {
            "fields": ("tipo", "assunto", "descricao")
        }),
        ("Status", {
            "fields": ("status", "status_kanban", "prioridade", "atendente")
        }),
        ("Rastreamento", {
            "fields": ("ip_address", "user_agent"),
            "classes": ["collapse"]
        }),
        ("Integracao IA/Chat", {
            "fields": ("chat_session_id", "ia_processed", "ia_response"),
            "classes": ["collapse"]
        }),
        ("Classificacao IA", {
            "fields": (
                "ia_categoria",
                "ia_prioridade_sugerida",
                "ia_resumo",
                "ia_problema_principal",
                "ia_palavras_chave",
                "ia_confianca",
                "ia_processed_at",
            ),
            "classes": ["collapse"]
        }),
        ("Recorrencia", {
            "fields": ("is_recorrente", "chamado_similar_ref", "similaridade_score"),
            "classes": ["collapse"]
        }),
        ("Auditoria", {
            "fields": ("created_at", "updated_at", "resolved_at", "closed_at", "created_by", "updated_by"),
            "classes": ["collapse"]
        }),
    )

    inlines = [AnexoChamadoInline, ComentarioChamadoInline, HistoricoChamadoInline]


@admin.register(AnexoChamado)
class AnexoChamadoAdmin(admin.ModelAdmin):
    list_display = ["nome_original", "chamado", "tipo", "tamanho", "created_at"]
    list_filter = ["tipo", "created_at"]
    search_fields = ["nome_original", "chamado__protocolo"]
    readonly_fields = ["id", "created_at"]


@admin.register(HistoricoChamado)
class HistoricoChamadoAdmin(admin.ModelAdmin):
    list_display = ["chamado", "tipo_acao", "descricao", "usuario", "created_at"]
    list_filter = ["tipo_acao", "created_at"]
    search_fields = ["chamado__protocolo", "descricao"]
    readonly_fields = ["id", "created_at"]


@admin.register(ComentarioChamado)
class ComentarioChamadoAdmin(admin.ModelAdmin):
    list_display = ["chamado", "tipo", "autor_nome", "is_from_client", "created_at"]
    list_filter = ["tipo", "is_from_client", "created_at"]
    search_fields = ["chamado__protocolo", "conteudo", "autor_nome"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(EmbeddingChamado)
class EmbeddingChamadoAdmin(admin.ModelAdmin):
    list_display = ["chamado", "texto_hash_short", "modelo", "created_at"]
    list_filter = ["modelo", "created_at"]
    search_fields = ["chamado__protocolo", "texto_base", "texto_hash"]
    readonly_fields = ["chamado", "embedding_vector", "texto_base", "texto_hash", "modelo", "created_at"]

    def texto_hash_short(self, obj):
        return f"{obj.texto_hash[:12]}..." if obj.texto_hash else "-"
    texto_hash_short.short_description = "Hash"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmbeddingCache)
class EmbeddingCacheAdmin(admin.ModelAdmin):
    list_display = ["texto_hash_short", "modelo", "uso_count", "created_at", "last_used_at"]
    list_filter = ["modelo", "created_at"]
    search_fields = ["texto_hash"]
    readonly_fields = ["texto_hash", "embedding_vector", "modelo", "uso_count", "created_at", "last_used_at"]
    ordering = ["-uso_count"]

    def texto_hash_short(self, obj):
        return f"{obj.texto_hash[:12]}..."
    texto_hash_short.short_description = "Hash"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "title", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["user__username", "user__email", "title", "message"]
    readonly_fields = ["id", "created_at", "read_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        ("Notificacao", {
            "fields": ("user", "notification_type", "title", "message", "chamado")
        }),
        ("Status", {
            "fields": ("is_read", "read_at")
        }),
        ("Auditoria", {
            "fields": ("created_at",)
        }),
    )

    def has_add_permission(self, request):
        # Notificacoes sao criadas automaticamente via signals
        return False


class WebhookLogInline(admin.TabularInline):
    model = WebhookLog
    extra = 0
    readonly_fields = ["id", "event", "status", "response_status_code", "retry_count", "created_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WebhookConfig)
class WebhookConfigAdmin(admin.ModelAdmin):
    list_display = ["name", "webhook_type", "is_active", "total_sent", "success_rate_display", "last_triggered_at"]
    list_filter = ["webhook_type", "is_active", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["id", "total_sent", "total_success", "total_failed", "last_triggered_at", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["name"]

    fieldsets = (
        ("Configuracao", {
            "fields": ("name", "webhook_type", "trigger_events", "is_active", "max_retries")
        }),
        ("URL (Criptografada)", {
            "fields": ("encrypted_url",),
            "description": "URL criptografada. Use a API para definir a URL em texto plano."
        }),
        ("Estatisticas", {
            "fields": ("total_sent", "total_success", "total_failed", "last_triggered_at")
        }),
        ("Auditoria", {
            "fields": ("created_at", "updated_at")
        }),
    )

    inlines = [WebhookLogInline]

    def success_rate_display(self, obj):
        if obj.total_sent == 0:
            return "0%"
        rate = (obj.total_success / obj.total_sent) * 100
        return f"{rate:.1f}%"
    success_rate_display.short_description = "Taxa de Sucesso"


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ["webhook", "chamado", "event", "status", "response_status_code", "retry_count", "created_at"]
    list_filter = ["status", "event", "created_at"]
    search_fields = ["webhook__name", "chamado__protocolo", "event"]
    readonly_fields = ["id", "webhook", "chamado", "event", "status", "payload_sent", "response_status_code", "response_body", "error_message", "retry_count", "created_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        ("Webhook", {
            "fields": ("webhook", "chamado", "event")
        }),
        ("Resultado", {
            "fields": ("status", "response_status_code", "retry_count")
        }),
        ("Detalhes", {
            "fields": ("payload_sent", "response_body", "error_message")
        }),
        ("Auditoria", {
            "fields": ("created_at",)
        }),
    )

    def has_add_permission(self, request):
        # Logs sao criados automaticamente
        return False

    def has_change_permission(self, request, obj=None):
        return False
