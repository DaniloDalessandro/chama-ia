from django.test import TestCase

from atendimento.ai.graph import _popular_resumo_atendimento, persistir_resultado_node
from atendimento.models import Atendimento


class PopularResumoAtendimentoTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def test_populates_resumo_servico_afetado_and_truncated_assunto(self):
        state = {
            "agente1_resultado": {
                "problema_identificado": "O sistema critico de pagamentos parou de responder para todos os clientes desde as 10h",
                "servico_afetado": "API de Pagamentos",
            }
        }
        _popular_resumo_atendimento(self.atendimento, state)

        self.atendimento.refresh_from_db()
        self.assertTrue(self.atendimento.resumo.startswith("O sistema critico de pagamentos"))
        self.assertEqual(self.atendimento.servico_afetado, "API de Pagamentos")
        self.assertEqual(len(self.atendimento.assunto), 80)
        self.assertTrue(self.atendimento.assunto.startswith("O sistema critico"))

    def test_degraded_fallback_text_becomes_resumo_honestly(self):
        state = {
            "agente1_resultado": {
                "problema_identificado": "Nao foi possivel determinar (DeepSeek indisponivel).",
                "servico_afetado": None,
                "dados_ausentes": True,
            }
        }
        _popular_resumo_atendimento(self.atendimento, state)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.resumo, "Nao foi possivel determinar (DeepSeek indisponivel).")
        self.assertEqual(self.atendimento.servico_afetado, "")
        self.assertEqual(self.atendimento.assunto, "Nao foi possivel determinar (DeepSeek indisponivel).")

    def test_empty_problema_falls_back_to_generic_assunto(self):
        state = {"agente1_resultado": {"problema_identificado": "", "servico_afetado": None}}
        _popular_resumo_atendimento(self.atendimento, state)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.assunto, f"Atendimento #{self.atendimento.id}")

    def test_missing_agente1_resultado_is_a_no_op(self):
        assunto_antes = self.atendimento.assunto
        _popular_resumo_atendimento(self.atendimento, {})
        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.assunto, assunto_antes)


class PersistirResultadoPopulatesEvenOnAgente6FailureTests(TestCase):
    def test_resumo_populated_even_when_agente6_failed(self):
        atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        state = {
            "atendimento_id": atendimento.id,
            "agente1_resultado": {"problema_identificado": "Erro critico no checkout", "servico_afetado": "Checkout"},
            "agente6_resultado": None,  # Agente 6 falhou (ex: sem VersaoAHP ativa)
            "versao_ahp_id": None,
        }

        resultado = persistir_resultado_node(state)

        self.assertIsNone(resultado["auditoria_id"])
        atendimento.refresh_from_db()
        self.assertEqual(atendimento.analise_ia_status, Atendimento.AnaliseIAStatus.ERRO)
        self.assertEqual(atendimento.resumo, "Erro critico no checkout")
        self.assertEqual(atendimento.servico_afetado, "Checkout")
