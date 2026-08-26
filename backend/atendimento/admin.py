from django.contrib import admin

from .models import (
    AnexoAtendimento,
    Atendimento,
    AuditoriaClassificacao,
    AvaliacaoCriterioAtendimento,
    MensagemAtendimento,
    RegraCriticaAtendimento,
    RevisaoHumanaAtendimento,
)


class MensagemAtendimentoInline(admin.TabularInline):
    model = MensagemAtendimento
    extra = 0
    readonly_fields = ("remetente_tipo", "conteudo", "criado_em")


class AvaliacaoCriterioInline(admin.TabularInline):
    model = AvaliacaoCriterioAtendimento
    extra = 0


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "email", "status_atendimento", "prioridade", "indice_ahp", "criado_em")
    list_filter = ("status_atendimento", "prioridade", "analise_ia_status")
    search_fields = ("nome", "email")
    readonly_fields = ("indice_ahp", "versao_ahp_utilizada")
    inlines = [MensagemAtendimentoInline, AvaliacaoCriterioInline]


@admin.register(AnexoAtendimento)
class AnexoAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("nome_original", "atendimento", "tipo_arquivo", "criado_em")


@admin.register(AuditoriaClassificacao)
class AuditoriaClassificacaoAdmin(admin.ModelAdmin):
    list_display = ("atendimento", "prioridade", "indice", "cr", "criado_em")
    readonly_fields = [f.name for f in AuditoriaClassificacao._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RegraCriticaAtendimento)
class RegraCriticaAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("atendimento", "confirmada", "origem")


@admin.register(RevisaoHumanaAtendimento)
class RevisaoHumanaAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("atendimento", "prioridade_anterior", "nova_prioridade", "responsavel", "criado_em")
