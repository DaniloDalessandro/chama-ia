from django.contrib import admin

from .models import Comparacao, Criterio, FaixaTempoEspera, Intensidade, Termo, VersaoAHP


@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "ativo", "regra_critica", "ordem")
    list_filter = ("ativo", "regra_critica", "exige_revisao_humana")
    search_fields = ("nome", "codigo", "descricao")

    def get_queryset(self, request):
        return Criterio.all_objects.all()


@admin.register(Intensidade)
class IntensidadeAdmin(admin.ModelAdmin):
    list_display = ("criterio", "codigo", "nome", "ativo", "ordem")
    list_filter = ("criterio", "codigo", "ativo")

    def get_queryset(self, request):
        return Intensidade.all_objects.all()


@admin.register(Termo)
class TermoAdmin(admin.ModelAdmin):
    list_display = ("termo", "criterio", "tipo_correspondencia", "status_aprovacao", "ativo")
    list_filter = ("criterio", "tipo_correspondencia", "status_aprovacao", "ativo")
    search_fields = ("termo", "descricao")

    def get_queryset(self, request):
        return Termo.all_objects.all()


@admin.register(FaixaTempoEspera)
class FaixaTempoEsperaAdmin(admin.ModelAdmin):
    list_display = ("criterio", "minutos_min", "minutos_max", "intensidade", "ativo")


@admin.register(VersaoAHP)
class VersaoAHPAdmin(admin.ModelAdmin):
    list_display = ("numero_versao", "estado", "ativada_em", "criado_em")
    list_filter = ("estado",)
    readonly_fields = (
        "numero_versao",
        "pesos_criterios",
        "lambda_max_criterios",
        "ci_criterios",
        "cr_criterios",
        "prioridades_intensidades",
        "lambda_max_intensidades",
        "ci_intensidades",
        "cr_intensidades",
        "p_max",
        "ativada_em",
        "ativada_por",
        "arquivada_em",
        "mensagens_erro",
    )


@admin.register(Comparacao)
class ComparacaoAdmin(admin.ModelAdmin):
    list_display = ("versao_ahp", "tipo", "criterio_contexto", "valor_saaty")
    list_filter = ("tipo", "versao_ahp")
