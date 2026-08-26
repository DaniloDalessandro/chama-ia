"""
AHPVersionService: maquina de estados do versionamento da hierarquia AHP.

RASCUNHO -> PROCESSANDO -> (VALIDA | INCONSISTENTE) -> ATIVA | ARQUIVADA | ERRO

Uma versao so pode ser ativada se TODAS as matrizes (criterios + intensidade
de cada criterio) forem consistentes (CR <= 0.10). Se qualquer uma delas for
inconsistente, a versao candidata vira INCONSISTENTE/ERRO e a versao ATIVA
anterior permanece intacta -- nunca ha ativacao parcial nem prioridade
"inventada" como fallback.
"""

from django.db import transaction
from django.utils import timezone

from ..models import VersaoAHP
from .comparison_service import AHPComparisonService
from .consistency_service import AHPConsistencyService
from .eigenvector_service import AHPEigenvectorService
from .hierarchy_service import AHPHierarchyService
from .intensity_service import AHPIntensityService
from .matrix_service import AHPMatrixService
from .synthesis_service import AHPSynthesisService


class InvalidStateTransitionError(Exception):
    """Transicao de estado invalida na maquina de estados da VersaoAHP."""


class AHPVersionService:
    @staticmethod
    @transaction.atomic
    def create_rascunho(descricao: str = "", user=None) -> VersaoAHP:
        return VersaoAHP.objects.create(
            descricao=descricao,
            estado=VersaoAHP.Estado.RASCUNHO,
            criado_por=user,
            atualizado_por=user,
        )

    @staticmethod
    def validar(versao_ahp: VersaoAHP) -> list:
        """
        Validacao somente-leitura: nao muda estado nem persiste nada. Retorna
        lista de mensagens de erro (vazia = a ativacao passaria desta etapa).
        """
        erros = []

        criterios = list(AHPHierarchyService.get_criterios_ativos())
        erros.extend(AHPHierarchyService.validate_mandatory_criterios(criterios))

        n_criterios = len(criterios)
        if n_criterios >= 2:
            valores_criterios = AHPComparisonService.get_valores_matrix_criterios(versao_ahp, criterios)
            erros.extend(
                f"[Criterios] {msg}"
                for msg in AHPMatrixService.validate_completeness(n_criterios, valores_criterios)
            )
            erros.extend(f"[Criterios] {msg}" for msg in AHPMatrixService.validate_values(valores_criterios))

        for criterio in criterios:
            intensidades = list(AHPIntensityService.get_comparable_intensidades(criterio))
            n_intensidades = len(intensidades)
            if n_intensidades < 2:
                erros.append(
                    f"[{criterio.codigo}] Sao necessarias ao menos 2 intensidades comparaveis "
                    "(exclui AUSENTE/INCONCLUSIVA)."
                )
                continue

            valores_intensidades = AHPComparisonService.get_valores_matrix_intensidades(
                versao_ahp, criterio, intensidades
            )
            erros.extend(
                f"[{criterio.codigo}] {msg}"
                for msg in AHPMatrixService.validate_completeness(n_intensidades, valores_intensidades)
            )
            erros.extend(
                f"[{criterio.codigo}] {msg}"
                for msg in AHPMatrixService.validate_values(valores_intensidades)
            )

        erros.extend(AHPVersionService._validate_faixas_tempo_espera(criterios))

        return erros

    @staticmethod
    def _validate_faixas_tempo_espera(criterios: list) -> list:
        from ..models import CODIGO_TEMPO_DE_ESPERA

        criterio_tempo = next((c for c in criterios if c.codigo == CODIGO_TEMPO_DE_ESPERA), None)
        if criterio_tempo is None:
            return []

        faixas = list(criterio_tempo.faixas_tempo.filter(ativo=True).order_by("minutos_min"))
        if not faixas:
            return [f"[{CODIGO_TEMPO_DE_ESPERA}] Nenhuma faixa de tempo de espera configurada."]

        erros = []
        anterior_max = 0
        for idx, faixa in enumerate(faixas):
            if faixa.minutos_min != anterior_max:
                erros.append(
                    f"[{CODIGO_TEMPO_DE_ESPERA}] Faixa '{faixa}' nao e contigua com a anterior "
                    f"(esperado inicio em {anterior_max}min)."
                )
            is_last = idx == len(faixas) - 1
            if faixa.minutos_max is None and not is_last:
                erros.append(
                    f"[{CODIGO_TEMPO_DE_ESPERA}] Apenas a ultima faixa pode ser aberta (sem minutos_max)."
                )
            anterior_max = faixa.minutos_max if faixa.minutos_max is not None else anterior_max
        return erros

    @staticmethod
    def _compute_criterios(versao_ahp: VersaoAHP, criterios: list) -> dict:
        """Calcula pesos/lambda_max/CI/CR da matriz de criterios. Nao persiste nada."""
        n = len(criterios)
        valores = AHPComparisonService.get_valores_matrix_criterios(versao_ahp, criterios)
        matrix = AHPMatrixService.build_matrix(n, valores)
        pesos, lambda_max = AHPEigenvectorService.compute(matrix)
        ci = AHPConsistencyService.compute_ci(lambda_max, n)
        cr, _ri = AHPConsistencyService.compute_cr(ci, n)
        return {
            "pesos": {criterio.codigo: float(pesos[idx]) for idx, criterio in enumerate(criterios)},
            "lambda_max": lambda_max,
            "ci": ci,
            "cr": cr,
        }

    @staticmethod
    def _compute_intensidades_criterio(versao_ahp: VersaoAHP, criterio) -> dict:
        """Calcula pesos/lambda_max/CI/CR da matriz de intensidades de um criterio. Nao persiste nada."""
        intensidades = list(AHPIntensityService.get_comparable_intensidades(criterio))
        n = len(intensidades)
        valores = AHPComparisonService.get_valores_matrix_intensidades(versao_ahp, criterio, intensidades)
        matrix = AHPMatrixService.build_matrix(n, valores)
        pesos, lambda_max = AHPEigenvectorService.compute(matrix)
        ci = AHPConsistencyService.compute_ci(lambda_max, n)
        cr, _ri = AHPConsistencyService.compute_cr(ci, n)
        return {
            "pesos": {intensidade.codigo: float(pesos[idx]) for idx, intensidade in enumerate(intensidades)},
            "lambda_max": lambda_max,
            "ci": ci,
            "cr": cr,
        }

    @staticmethod
    @transaction.atomic
    def ativar(versao_ahp: VersaoAHP, user=None) -> VersaoAHP:
        if versao_ahp.estado != VersaoAHP.Estado.RASCUNHO:
            raise InvalidStateTransitionError(
                f"Versao {versao_ahp.numero_versao} esta em '{versao_ahp.estado}', "
                "so e possivel ativar uma versao em RASCUNHO."
            )

        versao_ahp.estado = VersaoAHP.Estado.PROCESSANDO
        versao_ahp.atualizado_por = user
        versao_ahp.save(update_fields=["estado", "atualizado_por", "atualizado_em"])

        erros = AHPVersionService.validar(versao_ahp)
        if erros:
            return AHPVersionService._marcar_erro(versao_ahp, erros, user)

        try:
            criterios = list(AHPHierarchyService.get_criterios_ativos())
            resultado_criterios = AHPVersionService._compute_criterios(versao_ahp, criterios)

            if not AHPConsistencyService.is_consistent(resultado_criterios["cr"]):
                versao_ahp.lambda_max_criterios = resultado_criterios["lambda_max"]
                versao_ahp.ci_criterios = resultado_criterios["ci"]
                versao_ahp.cr_criterios = resultado_criterios["cr"]
                return AHPVersionService._marcar_inconsistente(
                    versao_ahp, [f"[Criterios] CR = {resultado_criterios['cr']:.4f} > 0.10"], user
                )

            prioridades_intensidades = {}
            lambda_max_intensidades = {}
            ci_intensidades = {}
            cr_intensidades = {}

            for criterio in criterios:
                resultado_int = AHPVersionService._compute_intensidades_criterio(versao_ahp, criterio)
                lambda_max_intensidades[criterio.codigo] = resultado_int["lambda_max"]
                ci_intensidades[criterio.codigo] = resultado_int["ci"]
                cr_intensidades[criterio.codigo] = resultado_int["cr"]

                if not AHPConsistencyService.is_consistent(resultado_int["cr"]):
                    versao_ahp.lambda_max_criterios = resultado_criterios["lambda_max"]
                    versao_ahp.ci_criterios = resultado_criterios["ci"]
                    versao_ahp.cr_criterios = resultado_criterios["cr"]
                    versao_ahp.lambda_max_intensidades = lambda_max_intensidades
                    versao_ahp.ci_intensidades = ci_intensidades
                    versao_ahp.cr_intensidades = cr_intensidades
                    return AHPVersionService._marcar_inconsistente(
                        versao_ahp, [f"[{criterio.codigo}] CR = {resultado_int['cr']:.4f} > 0.10"], user
                    )

                prioridades_intensidades[criterio.codigo] = resultado_int["pesos"]
        except Exception as exc:  # noqa: BLE001 - qualquer falha de calculo vira estado ERRO, nunca uma prioridade inventada
            return AHPVersionService._marcar_erro(versao_ahp, [f"Falha no calculo do AHP: {exc}"], user)

        p_max = AHPSynthesisService.compute_p_max(resultado_criterios["pesos"], prioridades_intensidades)

        versao_ahp.pesos_criterios = resultado_criterios["pesos"]
        versao_ahp.lambda_max_criterios = resultado_criterios["lambda_max"]
        versao_ahp.ci_criterios = resultado_criterios["ci"]
        versao_ahp.cr_criterios = resultado_criterios["cr"]
        versao_ahp.prioridades_intensidades = prioridades_intensidades
        versao_ahp.lambda_max_intensidades = lambda_max_intensidades
        versao_ahp.ci_intensidades = ci_intensidades
        versao_ahp.cr_intensidades = cr_intensidades
        versao_ahp.p_max = p_max
        versao_ahp.estado = VersaoAHP.Estado.VALIDA
        versao_ahp.mensagens_erro = []
        versao_ahp.save()

        anterior_ativa = VersaoAHP.objects.filter(estado=VersaoAHP.Estado.ATIVA).exclude(pk=versao_ahp.pk).first()
        if anterior_ativa is not None:
            anterior_ativa.estado = VersaoAHP.Estado.ARQUIVADA
            anterior_ativa.arquivada_em = timezone.now()
            anterior_ativa.atualizado_por = user
            anterior_ativa.save(update_fields=["estado", "arquivada_em", "atualizado_por", "atualizado_em"])

        versao_ahp.estado = VersaoAHP.Estado.ATIVA
        versao_ahp.ativada_em = timezone.now()
        versao_ahp.ativada_por = user
        versao_ahp.atualizado_por = user
        versao_ahp.save()

        return versao_ahp

    @staticmethod
    @transaction.atomic
    def recalcular(versao_ahp: VersaoAHP, user=None) -> VersaoAHP:
        """
        Recalcula pesos/lambda_max/CI/CR a partir das comparacoes cadastradas
        SEM mudar o estado da versao -- util para previsualizar numeros
        durante a edicao de um RASCUNHO, antes de decidir ativar.
        """
        if versao_ahp.estado != VersaoAHP.Estado.RASCUNHO:
            raise InvalidStateTransitionError(
                f"Versao {versao_ahp.numero_versao} esta em '{versao_ahp.estado}', "
                "so e possivel recalcular uma versao em RASCUNHO."
            )

        criterios = list(AHPHierarchyService.get_criterios_ativos())
        resultado_criterios = AHPVersionService._compute_criterios(versao_ahp, criterios)

        prioridades_intensidades = {}
        lambda_max_intensidades = {}
        ci_intensidades = {}
        cr_intensidades = {}
        for criterio in criterios:
            resultado_int = AHPVersionService._compute_intensidades_criterio(versao_ahp, criterio)
            prioridades_intensidades[criterio.codigo] = resultado_int["pesos"]
            lambda_max_intensidades[criterio.codigo] = resultado_int["lambda_max"]
            ci_intensidades[criterio.codigo] = resultado_int["ci"]
            cr_intensidades[criterio.codigo] = resultado_int["cr"]

        versao_ahp.pesos_criterios = resultado_criterios["pesos"]
        versao_ahp.lambda_max_criterios = resultado_criterios["lambda_max"]
        versao_ahp.ci_criterios = resultado_criterios["ci"]
        versao_ahp.cr_criterios = resultado_criterios["cr"]
        versao_ahp.prioridades_intensidades = prioridades_intensidades
        versao_ahp.lambda_max_intensidades = lambda_max_intensidades
        versao_ahp.ci_intensidades = ci_intensidades
        versao_ahp.cr_intensidades = cr_intensidades
        versao_ahp.p_max = AHPSynthesisService.compute_p_max(resultado_criterios["pesos"], prioridades_intensidades)
        versao_ahp.atualizado_por = user
        versao_ahp.save()
        return versao_ahp

    @staticmethod
    def _marcar_inconsistente(versao_ahp: VersaoAHP, erros: list, user=None) -> VersaoAHP:
        versao_ahp.estado = VersaoAHP.Estado.INCONSISTENTE
        versao_ahp.mensagens_erro = erros
        versao_ahp.atualizado_por = user
        versao_ahp.save()
        return versao_ahp

    @staticmethod
    def _marcar_erro(versao_ahp: VersaoAHP, erros: list, user=None) -> VersaoAHP:
        versao_ahp.estado = VersaoAHP.Estado.ERRO
        versao_ahp.mensagens_erro = erros
        versao_ahp.atualizado_por = user
        versao_ahp.save()
        return versao_ahp

    @staticmethod
    def get_versao_ativa():
        return VersaoAHP.objects.filter(estado=VersaoAHP.Estado.ATIVA).first()
