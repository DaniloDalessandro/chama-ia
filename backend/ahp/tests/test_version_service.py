from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
    VersaoAHP,
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.version_service import AHPVersionService, InvalidStateTransitionError

User = get_user_model()

# Matriz de criterios perfeitamente consistente, pesos [8,4,2,1] (ordem: URGENCIA,
# IMPACTO, SENTIMENTO, TEMPO_DE_ESPERA) -- todos os valores dentro da escala de Saaty.
VALORES_CRITERIOS_CONSISTENTES = {
    (0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0,
    (1, 2): 2.0, (1, 3): 4.0,
    (2, 3): 2.0,
}

# Matriz de intensidades (BAIXA, MODERADA, CRITICA) perfeitamente consistente, pesos [4,2,1].
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (1, 2): 2.0}

# Matriz de intensidades propositalmente inconsistente (CR ~= 0.14 > 0.10).
VALORES_INTENSIDADES_INCONSISTENTES = {(0, 1): 5.0, (0, 2): 6.0, (1, 2): 4.0}


class VersionServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterios = {}
        self.intensidades_comparaveis = {}

        for ordem, codigo in enumerate(
            [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1
        ):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio

            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(
                criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3
            )
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(
                criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5
            )
            self.intensidades_comparaveis[codigo] = [baixa, moderada, critica]

        criterio_tempo = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(
            criterio=criterio_tempo, minutos_min=0, minutos_max=5,
            intensidade=self.intensidades_comparaveis[CODIGO_TEMPO_DE_ESPERA][0], ordem=1,
        )
        FaixaTempoEspera.objects.create(
            criterio=criterio_tempo, minutos_min=5, minutos_max=15,
            intensidade=self.intensidades_comparaveis[CODIGO_TEMPO_DE_ESPERA][1], ordem=2,
        )
        FaixaTempoEspera.objects.create(
            criterio=criterio_tempo, minutos_min=15, minutos_max=None,
            intensidade=self.intensidades_comparaveis[CODIGO_TEMPO_DE_ESPERA][2], ordem=3,
        )

    def _criterios_ordenados(self):
        return [
            self.criterios[CODIGO_URGENCIA],
            self.criterios[CODIGO_IMPACTO_NO_CLIENTE],
            self.criterios[CODIGO_SENTIMENTO_DO_CLIENTE],
            self.criterios[CODIGO_TEMPO_DE_ESPERA],
        ]

    def _setup_rascunho(self, valores_intensidades_urgencia=None) -> VersaoAHP:
        versao = AHPVersionService.create_rascunho(descricao="teste", user=self.user)

        AHPComparisonService.save_comparacoes_criterios(
            versao, self._criterios_ordenados(), VALORES_CRITERIOS_CONSISTENTES, user=self.user
        )

        for codigo, criterio in self.criterios.items():
            valores = VALORES_INTENSIDADES_CONSISTENTES
            if codigo == CODIGO_URGENCIA and valores_intensidades_urgencia is not None:
                valores = valores_intensidades_urgencia
            AHPComparisonService.save_comparacoes_intensidades(
                versao, criterio, self.intensidades_comparaveis[codigo], valores, user=self.user
            )

        return versao

    def test_activation_happy_path(self):
        versao = self._setup_rascunho()

        resultado = AHPVersionService.ativar(versao, user=self.user)

        self.assertEqual(resultado.estado, VersaoAHP.Estado.ATIVA)
        self.assertIsNotNone(resultado.ativada_em)
        self.assertEqual(resultado.ativada_por, self.user)
        self.assertAlmostEqual(sum(resultado.pesos_criterios.values()), 1.0, places=6)
        self.assertAlmostEqual(resultado.cr_criterios, 0.0, places=6)
        self.assertIsNotNone(resultado.p_max)
        self.assertEqual(AHPVersionService.get_versao_ativa().pk, resultado.pk)

    def test_second_activation_archives_first(self):
        versao1 = self._setup_rascunho()
        AHPVersionService.ativar(versao1, user=self.user)

        versao2 = self._setup_rascunho()
        AHPVersionService.ativar(versao2, user=self.user)

        versao1.refresh_from_db()
        versao2.refresh_from_db()
        self.assertEqual(versao1.estado, VersaoAHP.Estado.ARQUIVADA)
        self.assertIsNotNone(versao1.arquivada_em)
        self.assertEqual(versao2.estado, VersaoAHP.Estado.ATIVA)

    def test_inconsistent_intensity_matrix_blocks_activation_and_preserves_previous_active(self):
        versao1 = self._setup_rascunho()
        AHPVersionService.ativar(versao1, user=self.user)

        versao2 = self._setup_rascunho(valores_intensidades_urgencia=VALORES_INTENSIDADES_INCONSISTENTES)
        resultado2 = AHPVersionService.ativar(versao2, user=self.user)

        self.assertEqual(resultado2.estado, VersaoAHP.Estado.INCONSISTENTE)
        self.assertTrue(resultado2.mensagens_erro)
        self.assertGreater(resultado2.cr_intensidades[CODIGO_URGENCIA], 0.10)

        versao1.refresh_from_db()
        self.assertEqual(versao1.estado, VersaoAHP.Estado.ATIVA)
        self.assertEqual(AHPVersionService.get_versao_ativa().pk, versao1.pk)

    def test_missing_mandatory_criterio_results_in_erro(self):
        criterio_tempo = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        criterio_tempo.ativo = False
        criterio_tempo.save()

        versao = self._setup_rascunho()
        resultado = AHPVersionService.ativar(versao, user=self.user)

        self.assertEqual(resultado.estado, VersaoAHP.Estado.ERRO)
        self.assertTrue(any("TEMPO_DE_ESPERA" in msg for msg in resultado.mensagens_erro))

    def test_validar_is_side_effect_free(self):
        versao = self._setup_rascunho()
        estado_antes = versao.estado

        erros = AHPVersionService.validar(versao)

        versao.refresh_from_db()
        self.assertEqual(erros, [])
        self.assertEqual(versao.estado, estado_antes)

    def test_cannot_activate_a_non_rascunho_version(self):
        versao = self._setup_rascunho()
        AHPVersionService.ativar(versao, user=self.user)

        with self.assertRaises(InvalidStateTransitionError):
            AHPVersionService.ativar(versao, user=self.user)

    def test_only_one_active_version_db_constraint(self):
        versao1 = self._setup_rascunho()
        AHPVersionService.ativar(versao1, user=self.user)

        versao2 = self._setup_rascunho()
        versao2.estado = VersaoAHP.Estado.ATIVA
        with self.assertRaises(Exception):
            with transaction.atomic():
                versao2.save()
