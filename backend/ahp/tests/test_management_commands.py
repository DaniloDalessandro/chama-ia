from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
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
from ahp.services.version_service import AHPVersionService

User = get_user_model()

VALORES_CRITERIOS_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (1, 2): 2.0}
VALORES_INTENSIDADES_INCONSISTENTES = {(0, 1): 5.0, (0, 2): 6.0, (1, 2): 4.0}


class ManagementCommandsTestCase(TestCase):
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

    def _criterios_ordenados(self):
        return [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]

    def _setup_rascunho(self, valores_intensidades_urgencia=None):
        versao = AHPVersionService.create_rascunho(descricao="teste", user=self.user)
        AHPComparisonService.save_comparacoes_criterios(versao, self._criterios_ordenados(), VALORES_CRITERIOS_CONSISTENTES, user=self.user)
        for codigo, criterio in self.criterios.items():
            valores = VALORES_INTENSIDADES_CONSISTENTES
            if codigo == CODIGO_URGENCIA and valores_intensidades_urgencia is not None:
                valores = valores_intensidades_urgencia
            AHPComparisonService.save_comparacoes_intensidades(versao, criterio, self.intensidades[codigo], valores, user=self.user)
        return versao


class ValidarConfiguracaoCommandTests(ManagementCommandsTestCase):
    def test_valid_configuration_succeeds(self):
        versao = self._setup_rascunho()
        out = StringIO()
        call_command("ahp_validar_configuracao", f"--versao-id={versao.id}", "--user-email=admin@test.com", stdout=out)
        self.assertIn("valida", out.getvalue())

    def test_invalid_configuration_raises_command_error(self):
        self.criterios[CODIGO_TEMPO_DE_ESPERA].ativo = False
        self.criterios[CODIGO_TEMPO_DE_ESPERA].save()
        versao = self._setup_rascunho()
        with self.assertRaises(CommandError):
            call_command("ahp_validar_configuracao", f"--versao-id={versao.id}", "--user-email=admin@test.com", stdout=StringIO())

    def test_unknown_user_raises_command_error(self):
        versao = self._setup_rascunho()
        with self.assertRaises(CommandError):
            call_command("ahp_validar_configuracao", f"--versao-id={versao.id}", "--user-email=naoexiste@test.com", stdout=StringIO())


class RecalcularCommandTests(ManagementCommandsTestCase):
    def test_recalcula_sem_mudar_estado(self):
        versao = self._setup_rascunho()
        out = StringIO()
        call_command("ahp_recalcular", f"--versao-id={versao.id}", "--user-email=admin@test.com", stdout=out)
        versao.refresh_from_db()
        self.assertEqual(versao.estado, VersaoAHP.Estado.RASCUNHO)
        self.assertIsNotNone(versao.cr_criterios)


class ExibirConsistenciaCommandTests(ManagementCommandsTestCase):
    def test_prints_cr_after_recalculo(self):
        versao = self._setup_rascunho()
        AHPVersionService.recalcular(versao, user=self.user)
        out = StringIO()
        call_command("ahp_exibir_consistencia", f"--versao-id={versao.id}", stdout=out)
        self.assertIn("CR=", out.getvalue())

    def test_raises_if_not_calculated_yet(self):
        versao = self._setup_rascunho()
        with self.assertRaises(CommandError):
            call_command("ahp_exibir_consistencia", f"--versao-id={versao.id}", stdout=StringIO())


class AtivarVersaoCommandTests(ManagementCommandsTestCase):
    def test_activates_successfully(self):
        versao = self._setup_rascunho()
        out = StringIO()
        call_command("ahp_ativar_versao", f"--versao-id={versao.id}", "--user-email=admin@test.com", stdout=out)
        versao.refresh_from_db()
        self.assertEqual(versao.estado, VersaoAHP.Estado.ATIVA)
        self.assertIn("ativada com sucesso", out.getvalue())

    def test_inconsistent_matrix_exits_non_zero(self):
        versao = self._setup_rascunho(valores_intensidades_urgencia=VALORES_INTENSIDADES_INCONSISTENTES)
        with self.assertRaises(CommandError):
            call_command("ahp_ativar_versao", f"--versao-id={versao.id}", "--user-email=admin@test.com", stdout=StringIO())
        versao.refresh_from_db()
        self.assertEqual(versao.estado, VersaoAHP.Estado.INCONSISTENTE)
