"""
AHPHierarchyService: leitura/validacao da hierarquia de criterios ativos.
"""

from django.db.models import QuerySet

from ..models import CODIGOS_CRITERIOS_OBRIGATORIOS, Criterio


class AHPHierarchyService:
    @staticmethod
    def get_criterios_ativos() -> QuerySet:
        return Criterio.objects.filter(ativo=True).order_by("ordem")

    @staticmethod
    def get_intensidades_for_criterio(criterio: Criterio) -> QuerySet:
        return criterio.intensidades.filter(ativo=True).order_by("ordem")

    @staticmethod
    def validate_mandatory_criterios(criterios_qs=None) -> list:
        """
        Confirma que os 4 criterios obrigatorios da hierarquia existem e estao
        ativos. Retorna lista de mensagens de erro (vazia = tudo ok).
        """
        if criterios_qs is None:
            criterios_qs = AHPHierarchyService.get_criterios_ativos()

        codigos_presentes = {criterio.codigo for criterio in criterios_qs}
        erros = []
        for codigo in CODIGOS_CRITERIOS_OBRIGATORIOS:
            if codigo not in codigos_presentes:
                erros.append(f"Criterio obrigatorio ausente ou inativo: {codigo}")
        return erros
