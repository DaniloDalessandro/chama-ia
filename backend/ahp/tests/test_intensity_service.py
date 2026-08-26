from django.test import TestCase

from ahp.models import Criterio, Intensidade, VersaoAHP
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.intensity_service import AHPIntensityService


class IntensityServiceTests(TestCase):
    def setUp(self):
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        self.ausente = Intensidade.objects.create(
            criterio=self.criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1
        )
        self.baixa = Intensidade.objects.create(
            criterio=self.criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2
        )
        self.moderada = Intensidade.objects.create(
            criterio=self.criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3
        )
        self.critica = Intensidade.objects.create(
            criterio=self.criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4
        )
        self.inconclusiva = Intensidade.objects.create(
            criterio=self.criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5
        )
        self.versao = VersaoAHP.objects.create(descricao="teste")

    def test_get_comparable_intensidades_excludes_ausente_and_inconclusiva(self):
        comparaveis = list(AHPIntensityService.get_comparable_intensidades(self.criterio))
        codigos = {i.codigo for i in comparaveis}
        self.assertEqual(codigos, {Intensidade.Codigo.BAIXA, Intensidade.Codigo.MODERADA, Intensidade.Codigo.CRITICA})

    def test_compute_priorities_sums_to_one(self):
        ordenadas = [self.baixa, self.moderada, self.critica]
        # pesos exatos [1,2,4] -> consistente
        valores = {(0, 1): 1 / 2, (0, 2): 1 / 4, (1, 2): 1 / 2}
        AHPComparisonService.save_comparacoes_intensidades(self.versao, self.criterio, ordenadas, valores)

        priorities = AHPIntensityService.compute_priorities(self.versao, self.criterio)

        self.assertAlmostEqual(sum(priorities.values()), 1.0, places=6)
        self.assertNotIn(Intensidade.Codigo.AUSENTE, priorities)
        self.assertNotIn(Intensidade.Codigo.INCONCLUSIVA, priorities)
        # critica (peso relativo 4) deve ter a maior prioridade
        self.assertGreater(priorities[Intensidade.Codigo.CRITICA], priorities[Intensidade.Codigo.BAIXA])

    def test_contribution_for_ausente_is_zero(self):
        self.assertEqual(AHPIntensityService.contribution_for(Intensidade.Codigo.AUSENTE, {}), 0.0)

    def test_contribution_for_inconclusiva_raises(self):
        with self.assertRaises(ValueError):
            AHPIntensityService.contribution_for(Intensidade.Codigo.INCONCLUSIVA, {})

    def test_contribution_for_known_code(self):
        priorities = {Intensidade.Codigo.BAIXA: 0.25}
        self.assertEqual(AHPIntensityService.contribution_for(Intensidade.Codigo.BAIXA, priorities), 0.25)
