from django.contrib.auth import get_user_model
from django.test import TestCase

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.version_service import AHPVersionService
from atendimento.models import Atendimento
from atendimento.services.classification_service import (
    NenhumaVersaoAtivaError,
    ServicePriorityClassificationService,
)

User = get_user_model()

VALORES_CRITERIOS_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
# indices 0=baixa, 1=moderada, 2=critica -- pesos resultantes [1,2,4]/7, ou seja
# CRITICA tem a maior prioridade (orientacao positiva: intensidade maior = prioridade maior).
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class ClassificarPorIndiceBoundaryTests(TestCase):
    def test_boundaries(self):
        casos = [
            (100.0, Atendimento.Prioridade.P1),
            (80.0, Atendimento.Prioridade.P1),
            (79.99, Atendimento.Prioridade.P2),
            (60.0, Atendimento.Prioridade.P2),
            (59.99, Atendimento.Prioridade.P3),
            (35.0, Atendimento.Prioridade.P3),
            (34.99, Atendimento.Prioridade.P4),
            (0.0, Atendimento.Prioridade.P4),
        ]
        for indice, esperado in casos:
            with self.subTest(indice=indice):
                self.assertEqual(ServicePriorityClassificationService.classificar_por_indice(indice), esperado)


class ClassifyEndToEndTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate(
            [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1
        ):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        criterio_tempo = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

        criterios_ordenados = [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        self.versao = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS_CONSISTENTES, user=self.user)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES_CONSISTENTES, user=self.user)
        AHPVersionService.ativar(self.versao, user=self.user)
        self.versao.refresh_from_db()

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def _avaliar(self, codigo_criterio, intensidade):
        from atendimento.models import AvaliacaoCriterioAtendimento

        AvaliacaoCriterioAtendimento.objects.create(
            atendimento=self.atendimento, criterio=self.criterios[codigo_criterio], intensidade=intensidade
        )

    def test_classify_with_all_criteria_critica_yields_p1(self):
        for codigo in self.criterios:
            self._avaliar(codigo, self.intensidades[codigo][2])  # critica

        resultado = ServicePriorityClassificationService.classify(self.atendimento)

        self.assertFalse(resultado.revisao_humana)
        self.assertAlmostEqual(resultado.indice, 100.0, places=3)
        self.assertEqual(resultado.prioridade, Atendimento.Prioridade.P1)

    def test_classify_with_all_criteria_baixa_yields_p4(self):
        for codigo in self.criterios:
            self._avaliar(codigo, self.intensidades[codigo][0])  # baixa

        resultado = ServicePriorityClassificationService.classify(self.atendimento)

        self.assertEqual(resultado.prioridade, Atendimento.Prioridade.P4)

    def test_inconclusiva_forces_revisao_humana(self):
        for codigo in self.criterios:
            self._avaliar(codigo, self.intensidades[codigo][2])
        inconclusiva = Intensidade.objects.get(criterio=self.criterios[CODIGO_URGENCIA], codigo=Intensidade.Codigo.INCONCLUSIVA)
        av = self.atendimento.avaliacoes.get(criterio=self.criterios[CODIGO_URGENCIA])
        av.intensidade = inconclusiva
        av.save()

        resultado = ServicePriorityClassificationService.classify(self.atendimento)

        self.assertTrue(resultado.revisao_humana)
        self.assertEqual(resultado.prioridade, Atendimento.Prioridade.REVISAO_HUMANA)
        self.assertIsNone(resultado.indice)
        self.assertTrue(any("URGENCIA" in m for m in resultado.motivos_revisao_humana))

    def test_missing_evaluation_forces_revisao_humana(self):
        # avalia so 3 dos 4 criterios
        codigos = list(self.criterios.keys())[:3]
        for codigo in codigos:
            self._avaliar(codigo, self.intensidades[codigo][1])

        resultado = ServicePriorityClassificationService.classify(self.atendimento)

        self.assertTrue(resultado.revisao_humana)
        self.assertEqual(resultado.prioridade, Atendimento.Prioridade.REVISAO_HUMANA)

    def test_no_active_version_raises(self):
        self.versao.estado = "arquivada"
        self.versao.save()
        atendimento2 = Atendimento.objects.create(nome="Outro", email="o@test.com")
        with self.assertRaises(NenhumaVersaoAtivaError):
            ServicePriorityClassificationService.classify(atendimento2)
