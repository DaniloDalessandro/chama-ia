from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from atendimento.ai.agents.agente2_visual_ocr import agente2_node


class Agente2NodeTests(SimpleTestCase):
    def test_no_image_attachments_returns_full_confidence_no_llm_call(self):
        resultado = agente2_node({"anexos_imagem_ocr": []})
        self.assertEqual(resultado["agente2_resultado"]["confianca_geral"], 1.0)
        self.assertEqual(resultado["erros"], [])

    @patch("atendimento.ai.agents.agente2_visual_ocr.build_deepseek_llm", return_value=None)
    def test_no_api_key_returns_fallback_with_limitacoes(self, mock_llm):
        state = {"anexos_imagem_ocr": [{"anexo_id": "abc", "disponivel": True, "texto": "ERR_500", "confianca": 0.8}]}
        resultado = agente2_node(state)
        self.assertEqual(set(resultado.keys()), {"agente2_resultado", "erros"})
        self.assertEqual(resultado["agente2_resultado"]["confianca_geral"], 0.0)
        self.assertEqual(len(resultado["erros"]), 1)

    @patch("atendimento.ai.agents.agente2_visual_ocr.build_deepseek_llm", return_value=None)
    def test_ocr_unavailable_attachment_recorded_as_limitacao(self, mock_llm):
        state = {"anexos_imagem_ocr": [{"anexo_id": "abc", "disponivel": False, "motivo": "Tesseract ausente"}]}
        resultado = agente2_node(state)
        self.assertTrue(any("Tesseract ausente" in lim for lim in resultado["agente2_resultado"]["limitacoes"]))

    @patch("atendimento.ai.agents.agente2_visual_ocr.build_deepseek_llm", return_value=MagicMock())
    @patch("atendimento.ai.agents.agente2_visual_ocr.build_chain")
    def test_valid_chain_output_merges_previous_limitacoes(self, mock_build_chain, mock_llm):
        fake_chain = MagicMock()
        fake_chain.invoke.return_value = {
            "evidencias": [], "erros_codigos_detectados": ["ERR_500"], "datas_horas_detectadas": [],
            "dados_sensiveis_detectados": False, "limitacoes": [], "confianca_geral": 0.7,
        }
        mock_build_chain.return_value = fake_chain

        state = {
            "anexos_imagem_ocr": [
                {"anexo_id": "img1", "disponivel": True, "texto": "ERR_500"},
                {"anexo_id": "img2", "disponivel": False, "motivo": "sem tesseract"},
            ]
        }
        resultado = agente2_node(state)

        self.assertEqual(resultado["agente2_resultado"]["erros_codigos_detectados"], ["ERR_500"])
        self.assertTrue(any("img2" in lim for lim in resultado["agente2_resultado"]["limitacoes"]))
        self.assertEqual(resultado["erros"], [])
