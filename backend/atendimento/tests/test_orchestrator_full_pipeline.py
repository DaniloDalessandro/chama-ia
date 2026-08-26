"""
Teste de integracao completo da Fase 2: 5 chains do DeepSeek mockadas com
saidas deterministicas fixas -> Agente 6 (AHP real, Fase 1) -> Agente 7
(Python) -> AuditoriaClassificacao real persistida. Nenhuma chamada de rede
real, nenhuma DEEPSEEK_API_KEY real.
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
from atendimento.ai.orchestrator import analisar_atendimento
from atendimento.models import Atendimento, AuditoriaClassificacao, MensagemAtendimento

User = get_user_model()

VALORES_CRITERIOS = {(0, 1): 2.0, (0, 2): 4.0, (0, 3): 8.0, (1, 2): 2.0, (1, 3): 4.0, (2, 3): 2.0}
VALORES_INTENSIDADES = {(0, 1): 0.5, (0, 2): 0.25, (1, 2): 0.5}


class OrchestratorFullPipelineTests(TestCase):
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

        self.atendimento = Atendimento.objects.create(nome="Cliente Final", email="final@test.com")
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE,
            conteudo="Sistema critico de pagamentos parou de funcionar para todos os usuarios",
        )

    def _mock_chain(self, modulo: str, retorno: dict):
        return patch(f"{modulo}.build_chain", return_value=self._fake_chain(retorno))

    @staticmethod
    def _fake_chain(retorno: dict):
        chain = MagicMock()
        chain.invoke.return_value = retorno
        return chain

    def test_full_pipeline_with_mocked_deepseek_reaches_expected_ahp_classification(self):
        with patch("atendimento.ai.agents.agente1_conversa.build_deepseek_llm", return_value=MagicMock()), \
             self._mock_chain("atendimento.ai.agents.agente1_conversa", {
                 "problema_identificado": "Sistema critico de pagamentos fora do ar",
                 "solicitacao_atual": "Preciso que restabelecam o servico com urgencia",
                 "confianca_geral": 0.9, "dados_ausentes": False,
             }), \
             patch("atendimento.ai.agents.agente3_termos_contexto.build_deepseek_llm", return_value=MagicMock()), \
             self._mock_chain("atendimento.ai.agents.agente3_termos_contexto", {
                 "termos_correspondidos": [], "negacoes_detectadas": [], "termos_sugeridos_novos": [],
                 "contexto_alterado": False, "confianca_geral": 0.8,
             }), \
             patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_deepseek_llm", return_value=MagicMock()), \
             self._mock_chain("atendimento.ai.agents.agente4_avaliacao_criterios", {
                 "avaliacoes": [
                     {"criterio_codigo": CODIGO_URGENCIA, "intensidade_codigo": "critica", "evidencia": "sistema critico parado", "origem": "agente_avaliacao", "justificativa": "x", "confianca": 0.9, "dados_ausentes": False},
                     {"criterio_codigo": CODIGO_IMPACTO_NO_CLIENTE, "intensidade_codigo": "critica", "evidencia": "todos os usuarios afetados", "origem": "agente_avaliacao", "justificativa": "x", "confianca": 0.9, "dados_ausentes": False},
                     {"criterio_codigo": CODIGO_SENTIMENTO_DO_CLIENTE, "intensidade_codigo": "moderada", "evidencia": "cliente preocupado mas cordial", "origem": "agente_avaliacao", "justificativa": "x", "confianca": 0.7, "dados_ausentes": False},
                 ]
             }), \
             patch("atendimento.ai.agents.agente5_validacao_critica.build_deepseek_llm", return_value=MagicMock()), \
             self._mock_chain("atendimento.ai.agents.agente5_validacao_critica", {
                 "regra_critica_confirmada": False, "confianca": 0.9,
             }):
            resultado = analisar_atendimento(self.atendimento.id)

        self.assertIsNotNone(resultado["auditoria_id"])
        auditoria = AuditoriaClassificacao.objects.get(id=resultado["auditoria_id"])

        # TEMPO_DE_ESPERA calculado deterministicamente (atendimento recem-criado -> faixa "baixa")
        self.assertEqual(auditoria.intensidades[CODIGO_TEMPO_DE_ESPERA], "baixa")
        self.assertAlmostEqual(auditoria.indice, 88.333, places=1)
        self.assertEqual(auditoria.prioridade, Atendimento.Prioridade.P1)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.prioridade, Atendimento.Prioridade.P1)
        self.assertEqual(self.atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.CONCLUIDA)
        self.assertEqual(self.atendimento.status_atendimento, Atendimento.StatusAtendimento.AGUARDANDO)
