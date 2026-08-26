from django.test import TestCase

from atendimento.models import Atendimento, MensagemAtendimento
from atendimento.services.conversation_extraction_service import ConversationExtractionService


class ConversationExtractionServiceTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def _add(self, tipo, conteudo):
        return MensagemAtendimento.objects.create(atendimento=self.atendimento, remetente_tipo=tipo, conteudo=conteudo)

    def test_empty_history(self):
        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)
        self.assertEqual(historico, [])

    def test_chronological_order(self):
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "primeira")
        self._add(MensagemAtendimento.RemetenteTipo.ATENDENTE, "segunda")
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "terceira")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)

        self.assertEqual([m["conteudo"] for m in historico], ["primeira", "segunda", "terceira"])

    def test_consecutive_duplicate_is_marked_not_removed(self):
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "Meu sistema esta fora do ar")
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "meu sistema  esta FORA do ar  ")  # normaliza igual

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)

        self.assertEqual(len(historico), 2)  # nada e removido
        self.assertFalse(historico[0]["duplicada"])
        self.assertTrue(historico[1]["duplicada"])
        self.assertTrue(historico[1]["ignorada"])

    def test_non_consecutive_repeats_not_marked_duplicate(self):
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "mensagem A")
        self._add(MensagemAtendimento.RemetenteTipo.ATENDENTE, "mensagem B")
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "mensagem A")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)

        self.assertFalse(historico[2]["duplicada"])

    def test_irrelevant_system_message_flagged(self):
        self._add(MensagemAtendimento.RemetenteTipo.SISTEMA, "Atendimento iniciado as 10:00")
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "Preciso de ajuda")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)

        self.assertTrue(historico[0]["ignorada"])
        self.assertIsNotNone(historico[0]["motivo_ignorada"])
        self.assertFalse(historico[1]["ignorada"])

    def test_relevant_system_message_not_flagged(self):
        self._add(MensagemAtendimento.RemetenteTipo.SISTEMA, "Chamado 0001/2026 criado a partir deste atendimento")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)

        self.assertFalse(historico[0]["ignorada"])

    def test_split_por_remetente(self):
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "c1")
        self._add(MensagemAtendimento.RemetenteTipo.ATENDENTE, "a1")
        self._add(MensagemAtendimento.RemetenteTipo.SISTEMA, "s1")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)
        split = ConversationExtractionService.split_por_remetente(historico)

        self.assertEqual(len(split["cliente"]), 1)
        self.assertEqual(len(split["atendente"]), 1)
        self.assertEqual(len(split["sistema"]), 1)

    def test_get_mensagem_atual_returns_latest_non_ignored_client_message(self):
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "primeira duvida")
        self._add(MensagemAtendimento.RemetenteTipo.ATENDENTE, "resposta")
        self._add(MensagemAtendimento.RemetenteTipo.CLIENTE, "ainda com problema")

        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)
        atual = ConversationExtractionService.get_mensagem_atual(historico)

        self.assertEqual(atual["conteudo"], "ainda com problema")

    def test_get_mensagem_atual_empty_when_no_client_messages(self):
        self._add(MensagemAtendimento.RemetenteTipo.ATENDENTE, "so atendente falou")
        historico = ConversationExtractionService.get_historico_ordenado(self.atendimento)
        self.assertEqual(ConversationExtractionService.get_mensagem_atual(historico), {})
