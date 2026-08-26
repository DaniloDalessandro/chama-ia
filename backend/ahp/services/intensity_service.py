"""
AHPIntensityService: prioridades das intensidades de um criterio, calculadas
via AHP a partir das comparacoes par-a-par cadastradas.

Regras fixas do dominio:
- AUSENTE nunca entra na matriz de comparacao (contribuicao sempre zero).
- INCONCLUSIVA nunca recebe peso numerico algum -- sua presenca em uma
  avaliacao deve forcar revisao humana antes mesmo de chegar na sintese
  (essa checagem e responsabilidade do app `atendimento`, nao deste servico).
"""

from django.db.models import QuerySet

from ..models import Criterio, Intensidade, VersaoAHP
from .comparison_service import AHPComparisonService
from .eigenvector_service import AHPEigenvectorService
from .matrix_service import AHPMatrixService

_EXCLUDED_CODES = {Intensidade.Codigo.AUSENTE, Intensidade.Codigo.INCONCLUSIVA}


class AHPIntensityService:
    @staticmethod
    def get_comparable_intensidades(criterio: Criterio) -> QuerySet:
        return criterio.intensidades.filter(ativo=True).exclude(codigo__in=_EXCLUDED_CODES).order_by("ordem")

    @staticmethod
    def compute_priorities(versao_ahp: VersaoAHP, criterio: Criterio) -> dict:
        """Retorna {intensidade_codigo: peso}, somando 1 entre as intensidades comparaveis."""
        intensidades = list(AHPIntensityService.get_comparable_intensidades(criterio))
        n = len(intensidades)
        if n < 1:
            raise ValueError(f"Criterio {criterio.codigo} nao possui intensidades comparaveis ativas.")

        valores = AHPComparisonService.get_valores_matrix_intensidades(versao_ahp, criterio, intensidades)
        matrix = AHPMatrixService.build_matrix(n, valores)
        weights, lambda_max = AHPEigenvectorService.compute(matrix)

        return {intensidade.codigo: float(weights[idx]) for idx, intensidade in enumerate(intensidades)}

    @staticmethod
    def contribution_for(intensidade_codigo: str, priorities: dict) -> float:
        if intensidade_codigo == Intensidade.Codigo.AUSENTE:
            return 0.0
        if intensidade_codigo == Intensidade.Codigo.INCONCLUSIVA:
            raise ValueError(
                "INCONCLUSIVA nunca recebe peso numerico -- o chamador deve tratar "
                "esse caso como revisao humana antes de calcular contribuicoes."
            )
        if intensidade_codigo not in priorities:
            raise ValueError(f"Intensidade '{intensidade_codigo}' nao encontrada nas prioridades calculadas.")
        return priorities[intensidade_codigo]
