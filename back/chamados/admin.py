from django.contrib import admin
from .models import Chamado, AnexoChamado, HistoricoChamado, ComentarioChamado


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
        "tipo",
        "assunto",
        "status",
        "prioridade",
        "atendente",
        "created_at",
    ]
    list_filter = ["status", "prioridade", "tipo", "origem", "created_at"]
    search_fields = ["protocolo", "nome", "email", "assunto", "descricao"]
    readonly_fields = [
        "protocolo",
        "ip_address",
        "user_agent",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
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
            "fields": ("status", "prioridade", "atendente")
        }),
        ("Rastreamento", {
            "fields": ("ip_address", "user_agent"),
            "classes": ["collapse"]
        }),
        ("Integracao IA/Chat", {
            "fields": ("chat_session_id", "ia_processed", "ia_response"),
            "classes": ["collapse"]
        }),
        ("Auditoria", {
            "fields": ("created_at", "updated_at", "resolved_at", "closed_at"),
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
