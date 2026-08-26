"""
AHPComparisonService: persistencia das comparacoes par-a-par (Comparacao),
tanto para criterios quanto para intensidades de um criterio de contexto.

Escrita so e permitida enquanto a VersaoAHP estiver em RASCUNHO -- uma vez
que a versao sai desse estado (VALIDA/INCONSISTENTE/ATIVA/ARQUIVADA/ERRO),
as comparacoes ficam imutaveis (congeladas), preservando o historico.
"""

from django.db import transaction

from ..models import Comparacao, Criterio, Intensidade, VersaoAHP


class VersaoNaoEditavelError(Exception):
    """A versao AHP nao esta em estado RASCUNHO e nao pode receber novas comparacoes."""


class AHPComparisonService:
    @staticmethod
    def _assert_editable(versao_ahp: VersaoAHP) -> None:
        if versao_ahp.estado != VersaoAHP.Estado.RASCUNHO:
            raise VersaoNaoEditavelError(
                f"Versao AHP {versao_ahp.numero_versao} esta em estado "
                f"'{versao_ahp.estado}' e nao pode ser editada (apenas RASCUNHO)."
            )

    @staticmethod
    @transaction.atomic
    def save_comparacoes_criterios(versao_ahp: VersaoAHP, criterios_ordenados: list, valores: dict, user=None) -> list:
        """
        valores: {(i, j): valor_saaty} com i < j, indices posicionais em
        `criterios_ordenados`.
        """
        AHPComparisonService._assert_editable(versao_ahp)

        Comparacao.objects.filter(versao_ahp=versao_ahp, tipo=Comparacao.Tipo.CRITERIOS).delete()

        criadas = []
        for (i, j), valor in valores.items():
            criadas.append(
                Comparacao.objects.create(
                    versao_ahp=versao_ahp,
                    tipo=Comparacao.Tipo.CRITERIOS,
                    criterio_linha=criterios_ordenados[i],
                    criterio_coluna=criterios_ordenados[j],
                    valor_saaty=valor,
                    criado_por=user,
                    atualizado_por=user,
                )
            )
        return criadas

    @staticmethod
    @transaction.atomic
    def save_comparacoes_intensidades(
        versao_ahp: VersaoAHP, criterio_contexto: Criterio, intensidades_ordenadas: list, valores: dict, user=None
    ) -> list:
        AHPComparisonService._assert_editable(versao_ahp)

        Comparacao.objects.filter(
            versao_ahp=versao_ahp,
            tipo=Comparacao.Tipo.INTENSIDADES,
            criterio_contexto=criterio_contexto,
        ).delete()

        criadas = []
        for (i, j), valor in valores.items():
            criadas.append(
                Comparacao.objects.create(
                    versao_ahp=versao_ahp,
                    tipo=Comparacao.Tipo.INTENSIDADES,
                    criterio_contexto=criterio_contexto,
                    intensidade_linha=intensidades_ordenadas[i],
                    intensidade_coluna=intensidades_ordenadas[j],
                    valor_saaty=valor,
                    criado_por=user,
                    atualizado_por=user,
                )
            )
        return criadas

    @staticmethod
    def get_valores_matrix_criterios(versao_ahp: VersaoAHP, criterios_ordenados: list) -> dict:
        posicao_por_id = {criterio.id: idx for idx, criterio in enumerate(criterios_ordenados)}
        qs = Comparacao.objects.filter(versao_ahp=versao_ahp, tipo=Comparacao.Tipo.CRITERIOS)

        valores = {}
        for comparacao in qs:
            i = posicao_por_id.get(comparacao.criterio_linha_id)
            j = posicao_por_id.get(comparacao.criterio_coluna_id)
            if i is None or j is None:
                continue
            valores[(i, j)] = comparacao.valor_saaty
        return valores

    @staticmethod
    def get_valores_matrix_intensidades(versao_ahp: VersaoAHP, criterio_contexto: Criterio, intensidades_ordenadas: list) -> dict:
        posicao_por_id = {intensidade.id: idx for idx, intensidade in enumerate(intensidades_ordenadas)}
        qs = Comparacao.objects.filter(
            versao_ahp=versao_ahp,
            tipo=Comparacao.Tipo.INTENSIDADES,
            criterio_contexto=criterio_contexto,
        )

        valores = {}
        for comparacao in qs:
            i = posicao_por_id.get(comparacao.intensidade_linha_id)
            j = posicao_por_id.get(comparacao.intensidade_coluna_id)
            if i is None or j is None:
                continue
            valores[(i, j)] = comparacao.valor_saaty
        return valores
