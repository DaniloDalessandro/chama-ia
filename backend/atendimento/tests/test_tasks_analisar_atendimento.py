"""
Testes de `atendimento.tasks.analisar_atendimento_ia_task`. A task e chamada
DIRETAMENTE (nao via `.delay()`), o jeito padrao de testar tasks Celery sem
precisar de um broker real -- Celery faz o bind de `self` automaticamente
mesmo em chamada direta.
"""

from unittest.mock import MagicMock, patch

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
from atendimento.models import Atendimento, AuditoriaClassificacao, MensagemAtendimento
from atendimento.tasks import analisar_atendimento_ia_task

User = get_user_model()

VALORES_CRITERIOS = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class AnalisarAtendimentoTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate([CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        ct = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=ct, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

        criterios_ordenados = [self.criterios[c] for c in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA]]
        self.versao = AHPVersionService.create_rascunho(user=self.user)
        AHPComparisonService.save_comparacoes_criterios(self.versao, criterios_ordenados, VALORES_CRITERIOS, user=self.user)
        for codigo, criterio in self.criterios.items():
            AHPComparisonService.save_comparacoes_intensidades(self.versao, criterio, self.intensidades[codigo], VALORES_INTENSIDADES, user=self.user)
        AHPVersionService.ativar(self.versao, user=self.user)

        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE, conteudo="Sistema fora do ar",
        )
        self._patch_llm_none()

    def _patch_llm_none(self):
        modulos = [
            "atendimento.ai.agents.agente1_conversa", "atendimento.ai.agents.agente2_visual_ocr",
            "atendimento.ai.agents.agente3_termos_contexto", "atendimento.ai.agents.agente4_avaliacao_criterios",
            "atendimento.ai.agents.agente5_validacao_critica",
        ]
        for modulo in modulos:
            p = patch(f"{modulo}.build_deepseek_llm", return_value=None)
            p.start()
            self.addCleanup(p.stop)

    def test_direct_call_runs_synchronously_to_concluida(self):
        resultado = analisar_atendimento_ia_task(self.atendimento.id)

        self.assertTrue(resultado["success"])
        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.CONCLUIDA)

    def test_unknown_atendimento_returns_failure_without_raising(self):
        resultado = analisar_atendimento_ia_task(999999)
        self.assertFalse(resultado["success"])

    def test_calling_twice_creates_two_auditoria_rows_append_only(self):
        analisar_atendimento_ia_task(self.atendimento.id)
        analisar_atendimento_ia_task(self.atendimento.id)

        self.assertEqual(AuditoriaClassificacao.objects.filter(atendimento=self.atendimento).count(), 2)

    def test_unhandled_exception_marks_erro_never_stuck_on_processando(self):
        with patch("atendimento.ai.orchestrator.analisar_atendimento", side_effect=RuntimeError("falha total")):
            try:
                analisar_atendimento_ia_task(self.atendimento.id)
            except Exception:
                pass  # self.retry() pode levantar; o que importa e o estado gravado antes disso

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.ERRO)
        self.assertNotEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.PROCESSANDO)

    def test_never_touches_status_atendimento(self):
        status_antes = self.atendimento.status_atendimento
        analisar_atendimento_ia_task(self.atendimento.id)
        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.status_atendimento, status_antes)
