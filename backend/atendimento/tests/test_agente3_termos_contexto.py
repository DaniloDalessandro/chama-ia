from unittest.mock import MagicMock, patch

from django.test import TestCase

from ahp.models import Criterio, Intensidade, Termo
from atendimento.ai.agents.agente3_termos_contexto import agente3_node, _termos_candidatos_texto


class Agente3NodeTests(TestCase):
    def setUp(self):
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        Intensidade.objects.create(criterio=self.criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE)
        self.moderada = Intensidade.objects.create(criterio=self.criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA)
        self.termo_aprovado = Termo.objects.create(
            criterio=self.criterio, termo="prazo legal", intensidade_base=self.moderada,
            status_aprovacao=Termo.StatusAprovacao.APROVADO,
        )
        self.termo_pendente = Termo.objects.create(
            criterio=self.criterio, termo="termo ainda nao revisado", intensidade_base=self.moderada,
            status_aprovacao=Termo.StatusAprovacao.PENDENTE_APROVACAO,
        )
        self.state = {"agente1_resultado": {"problema_identificado": "x", "solicitacao_atual": "y", "evidencias": []}, "agente2_resultado": {}}

    def test_candidatos_excludes_pendente_aprovacao(self):
        texto = _termos_candidatos_texto()
        self.assertIn("prazo legal", texto)
        self.assertNotIn("termo ainda nao revisado", texto)

    @patch("atendimento.ai.agents.agente3_termos_contexto.build_deepseek_llm", return_value=None)
    def test_no_api_key_returns_fallback(self, mock_llm):
        resultado = agente3_node(self.state)
        self.assertEqual(set(resultado.keys()), {"agente3_resultado", "erros"})
        self.assertEqual(resultado["agente3_resultado"]["confianca_geral"], 0.0)
        self.assertEqual(len(resultado["erros"]), 1)

    @patch("atendimento.ai.agents.agente3_termos_contexto.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente3_termos_contexto.build_chain")
    def test_suggested_term_is_created_as_pendente_aprovacao(self, mock_build_chain, mock_llm):
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "termos_correspondidos": [],
            "negacoes_detectadas": [],
            "termos_sugeridos_novos": [
                {"termo": "sistema critico parado", "criterio_codigo": "URGENCIA", "justificativa": "aparece varias vezes"}
            ],
            "contexto_alterado": False,
            "confianca_geral": 0.6,
        }
        mock_build_chain.return_value = fake_chain

        resultado = agente3_node(self.state)

        novo_termo = Termo.objects.get(termo="sistema critico parado")
        self.assertEqual(novo_termo.status_aprovacao, Termo.StatusAprovacao.PENDENTE_APROVACAO)
        self.assertEqual(novo_termo.criterio, self.criterio)
        self.assertEqual(resultado["erros"], [])

    @patch("atendimento.ai.agents.agente3_termos_contexto.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente3_termos_contexto.build_chain")
    def test_suggested_term_with_unknown_criterio_is_skipped_not_raised(self, mock_build_chain, mock_llm):
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "termos_correspondidos": [], "negacoes_detectadas": [],
            "termos_sugeridos_novos": [{"termo": "x", "criterio_codigo": "CRITERIO_INEXISTENTE", "justificativa": "y"}],
            "contexto_alterado": False, "confianca_geral": 0.5,
        }
        mock_build_chain.return_value = fake_chain

        agente3_node(self.state)  # nao deve levantar

        self.assertFalse(Termo.objects.filter(termo="x").exists())

    @patch("atendimento.ai.agents.agente3_termos_contexto.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente3_termos_contexto.build_chain")
    def test_negation_and_temporality_case_from_spec(self, mock_build_chain, mock_llm):
        # "o sistema estava fora do ar, mas ja voltou" != "o sistema esta fora do ar"
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "termos_correspondidos": [
                {"termo_id": self.termo_aprovado.id, "criterio_codigo": "URGENCIA", "tipo_match": "expressao", "trecho_evidencia": "estava fora do ar", "confianca": 0.7}
            ],
            "negacoes_detectadas": [
                {"trecho": "mas ja voltou", "termo_afetado": "fora do ar", "efeito": "temporal_passado"}
            ],
            "termos_sugeridos_novos": [],
            "contexto_alterado": True,
            "confianca_geral": 0.8,
        }
        mock_build_chain.return_value = fake_chain

        resultado = agente3_node(self.state)

        self.assertEqual(resultado["agente3_resultado"]["negacoes_detectadas"][0]["efeito"], "temporal_passado")
        self.assertTrue(resultado["agente3_resultado"]["contexto_alterado"])
