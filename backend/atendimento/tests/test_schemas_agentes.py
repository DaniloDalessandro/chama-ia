from django.test import SimpleTestCase
from pydantic import ValidationError

from atendimento.ai.schemas import (
    Agente1ConversaOutput,
    Agente2VisualOutput,
    Agente3TermosOutput,
    Agente4AvaliacaoOutput,
    Agente5ValidacaoOutput,
    EvidenciaItem,
)


class EvidenciaItemTests(SimpleTestCase):
    def test_valid_evidencia_parses(self):
        item = EvidenciaItem(texto="sistema fora do ar", origem="mensagem_cliente", confianca=0.9)
        self.assertEqual(item.origem, "mensagem_cliente")

    def test_invalid_origem_raises(self):
        with self.assertRaises(ValidationError):
            EvidenciaItem(texto="x", origem="origem_invalida", confianca=0.5)

    def test_confianca_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            EvidenciaItem(texto="x", origem="historico", confianca=1.5)


class Agente1OutputTests(SimpleTestCase):
    def test_valid_output_parses(self):
        saida = Agente1ConversaOutput(
            problema_identificado="Sistema fora do ar", solicitacao_atual="Preciso de ajuda urgente", confianca_geral=0.8,
        )
        self.assertEqual(saida.evidencias, [])
        self.assertFalse(saida.dados_ausentes)

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValidationError):
            Agente1ConversaOutput(solicitacao_atual="x", confianca_geral=0.5)  # falta problema_identificado


class Agente2OutputTests(SimpleTestCase):
    def test_valid_output_parses(self):
        saida = Agente2VisualOutput(confianca_geral=0.5)
        self.assertEqual(saida.limitacoes, [])


class Agente3OutputTests(SimpleTestCase):
    def test_valid_output_with_termo_sugerido(self):
        saida = Agente3TermosOutput(
            termos_sugeridos_novos=[{"termo": "prazo legal", "criterio_codigo": "URGENCIA", "justificativa": "x"}],
            confianca_geral=0.7,
        )
        self.assertEqual(len(saida.termos_sugeridos_novos), 1)

    def test_invalid_tipo_match_raises(self):
        with self.assertRaises(ValidationError):
            Agente3TermosOutput(
                termos_correspondidos=[
                    {"termo_id": 1, "criterio_codigo": "URGENCIA", "tipo_match": "chute", "trecho_evidencia": "x", "confianca": 0.5}
                ],
                confianca_geral=0.5,
            )


class Agente4OutputTests(SimpleTestCase):
    def _avaliacao(self, criterio):
        return {
            "criterio_codigo": criterio, "intensidade_codigo": "moderada", "evidencia": "x",
            "origem": "agente_avaliacao", "justificativa": "x", "confianca": 0.6,
        }

    def test_requires_exactly_three_avaliacoes(self):
        saida = Agente4AvaliacaoOutput(avaliacoes=[
            self._avaliacao("URGENCIA"), self._avaliacao("IMPACTO_NO_CLIENTE"), self._avaliacao("SENTIMENTO_DO_CLIENTE"),
        ])
        self.assertEqual(len(saida.avaliacoes), 3)

    def test_tempo_de_espera_is_not_a_valid_criterio_codigo(self):
        with self.assertRaises(ValidationError):
            Agente4AvaliacaoOutput(avaliacoes=[
                self._avaliacao("URGENCIA"), self._avaliacao("IMPACTO_NO_CLIENTE"), self._avaliacao("TEMPO_DE_ESPERA"),
            ])

    def test_wrong_count_raises(self):
        with self.assertRaises(ValidationError):
            Agente4AvaliacaoOutput(avaliacoes=[self._avaliacao("URGENCIA")])


class Agente5OutputTests(SimpleTestCase):
    def test_defaults_are_safe(self):
        saida = Agente5ValidacaoOutput()
        self.assertFalse(saida.regra_critica_confirmada)
        self.assertFalse(saida.tentativa_manipulacao_detectada)
