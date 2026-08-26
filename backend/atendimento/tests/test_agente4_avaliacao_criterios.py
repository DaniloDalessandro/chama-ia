from unittest.mock import MagicMock, patch

from django.test import TestCase

from ahp.models import CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_URGENCIA, Criterio, Intensidade
from atendimento.ai.agents.agente4_avaliacao_criterios import agente4_node


class Agente4NodeTests(TestCase):
    def setUp(self):
        for codigo in [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE]:
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo)
            Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA)
            Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA)

        self.state = {
            "agente1_resultado": {"problema_identificado": "Sistema fora do ar"},
            "agente2_resultado": {"evidencias": []},
            "agente3_resultado": {"termos_correspondidos": []},
        }

    def _avaliacao(self, criterio, intensidade):
        return {
            "criterio_codigo": criterio, "intensidade_codigo": intensidade, "evidencia": "x",
            "origem": "agente_avaliacao", "justificativa": "x", "confianca": 0.7, "dados_ausentes": False,
        }

    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_deepseek_llm", return_value=None)
    def test_no_api_key_returns_inconclusiva_fallback_for_all_three(self, mock_llm):
        resultado = agente4_node(self.state)

        self.assertEqual(set(resultado.keys()), {"agente4_resultado", "erros"})
        avaliacoes = resultado["agente4_resultado"]["avaliacoes"]
        self.assertEqual(len(avaliacoes), 3)
        self.assertTrue(all(a["intensidade_codigo"] == "inconclusiva" for a in avaliacoes))
        self.assertTrue(all(a["dados_ausentes"] for a in avaliacoes))

    def test_tempo_de_espera_never_appears_in_criterios_avaliados(self):
        from atendimento.ai.agents.agente4_avaliacao_criterios import _CRITERIOS_INTERPRETATIVOS
        self.assertNotIn("TEMPO_DE_ESPERA", _CRITERIOS_INTERPRETATIVOS)
        self.assertEqual(len(_CRITERIOS_INTERPRETATIVOS), 3)

    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_chain")
    def test_valid_output_with_real_intensidades_passes_through(self, mock_build_chain, mock_llm):
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "avaliacoes": [
                self._avaliacao(CODIGO_URGENCIA, "critica"),
                self._avaliacao(CODIGO_IMPACTO_NO_CLIENTE, "moderada"),
                self._avaliacao(CODIGO_SENTIMENTO_DO_CLIENTE, "moderada"),
            ]
        }
        mock_build_chain.return_value = fake_chain

        resultado = agente4_node(self.state)

        self.assertEqual(resultado["erros"], [])
        codigos = {a["criterio_codigo"]: a["intensidade_codigo"] for a in resultado["agente4_resultado"]["avaliacoes"]}
        self.assertEqual(codigos[CODIGO_URGENCIA], "critica")

    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_chain")
    def test_hallucinated_intensidade_is_corrected_to_inconclusiva(self, mock_build_chain, mock_llm):
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "avaliacoes": [
                self._avaliacao(CODIGO_URGENCIA, "extremamente_critica"),  # nao existe -- alucinacao
                self._avaliacao(CODIGO_IMPACTO_NO_CLIENTE, "moderada"),
                self._avaliacao(CODIGO_SENTIMENTO_DO_CLIENTE, "moderada"),
            ]
        }
        mock_build_chain.return_value = fake_chain

        resultado = agente4_node(self.state)

        avaliacao_urgencia = next(a for a in resultado["agente4_resultado"]["avaliacoes"] if a["criterio_codigo"] == CODIGO_URGENCIA)
        self.assertEqual(avaliacao_urgencia["intensidade_codigo"], "inconclusiva")
        self.assertTrue(avaliacao_urgencia["dados_ausentes"])
        self.assertEqual(len(resultado["erros"]), 1)
        self.assertIn("extremamente_critica", resultado["erros"][0]["erro"])

    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente4_avaliacao_criterios.build_chain")
    def test_irritated_sentiment_alone_does_not_force_urgencia(self, mock_build_chain, mock_llm):
        """Um sentimento negativo isolado nao deve, por si so, forcar urgencia/impacto altos --
        isso e garantido pela independencia dos 3 valores retornados pela LLM (mock aqui
        simula uma avaliacao deliberadamente independente por criterio)."""
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "avaliacoes": [
                self._avaliacao(CODIGO_URGENCIA, "moderada"),
                self._avaliacao(CODIGO_IMPACTO_NO_CLIENTE, "moderada"),
                self._avaliacao(CODIGO_SENTIMENTO_DO_CLIENTE, "critica"),
            ]
        }
        mock_build_chain.return_value = fake_chain

        resultado = agente4_node(self.state)
        codigos = {a["criterio_codigo"]: a["intensidade_codigo"] for a in resultado["agente4_resultado"]["avaliacoes"]}

        self.assertEqual(codigos[CODIGO_SENTIMENTO_DO_CLIENTE], "critica")
        self.assertEqual(codigos[CODIGO_URGENCIA], "moderada")
