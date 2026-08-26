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
)
from ahp.services.comparison_service import AHPComparisonService
from ahp.services.version_service import AHPVersionService
from atendimento.models import Atendimento, AuditoriaClassificacao

User = get_user_model()

VALORES_CRITERIOS_CONSISTENTES = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES_CONSISTENTES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class TestarPriorizacaoCommandTests(TestCase):
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

    def _intensidades_arg(self):
        return "URGENCIA=critica,IMPACTO_NO_CLIENTE=critica,SENTIMENTO_DO_CLIENTE=critica,TEMPO_DE_ESPERA=critica"

    def test_synthetic_run_does_not_persist(self):
        out = StringIO()
        call_command(
            "ahp_testar_priorizacao", f"--versao-id={self.versao.id}", "--user-email=admin@test.com",
            f"--intensidades={self._intensidades_arg()}", stdout=out,
        )
        self.assertIn("SIMULACAO", out.getvalue())
        self.assertIn("Indice = 100.00", out.getvalue())
        self.assertEqual(AuditoriaClassificacao.objects.count(), 0)

    def test_run_with_atendimento_id_persists(self):
        atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        out = StringIO()
        call_command(
            "ahp_testar_priorizacao", f"--versao-id={self.versao.id}", "--user-email=admin@test.com",
            f"--intensidades={self._intensidades_arg()}", f"--atendimento-id={atendimento.id}", stdout=out,
        )
        self.assertIn("PERSISTIDO", out.getvalue())
        auditoria = AuditoriaClassificacao.objects.get(atendimento=atendimento)
        self.assertEqual(auditoria.criado_por, self.user)
        self.assertEqual(auditoria.prioridade, Atendimento.Prioridade.P1)

    def test_invalid_email_raises(self):
        with self.assertRaises(CommandError):
            call_command(
                "ahp_testar_priorizacao", f"--versao-id={self.versao.id}", "--user-email=nao-existe@test.com",
                f"--intensidades={self._intensidades_arg()}", stdout=StringIO(),
            )
