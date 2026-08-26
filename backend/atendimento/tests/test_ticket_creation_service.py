from django.contrib.auth import get_user_model
from django.test import TestCase

from atendimento.models import Atendimento, MensagemAtendimento
from atendimento.services.ticket_creation_service import TicketCreationService
from chamados.models import Chamado

User = get_user_model()


class TicketCreationServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.atendimento = Atendimento.objects.create(
            nome="Cliente Teste", email="cliente@test.com", telefone="11999999999",
            prioridade=Atendimento.Prioridade.P2,
        )
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE,
            conteudo="Meu sistema esta fora do ar",
        )
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.ATENDENTE,
            conteudo="Vou verificar e abrir um chamado para a equipe tecnica.",
        )

    def test_creates_chamado_linked_to_atendimento(self):
        chamado = TicketCreationService.create_from_atendimento(self.atendimento, motivo="Requer equipe tecnica", user=self.user)

        self.assertEqual(chamado.atendimento_origem_id, self.atendimento.id)
        self.assertEqual(chamado.motivo_encaminhamento, "Requer equipe tecnica")
        self.assertEqual(chamado.prioridade_calculada_atendimento, Atendimento.Prioridade.P2)
        self.assertEqual(chamado.email, self.atendimento.email)
        self.assertIn("fora do ar", chamado.descricao)
        self.assertIsNotNone(chamado.protocolo)
        self.assertTrue(chamado.protocolo.endswith("/2026"))

    def test_atendimento_transitions_to_encaminhado_but_stays_intact(self):
        nome_antes = self.atendimento.nome
        email_antes = self.atendimento.email
        mensagens_antes = self.atendimento.mensagens.count()

        TicketCreationService.create_from_atendimento(self.atendimento, motivo="x", user=self.user)

        self.atendimento.refresh_from_db()
        self.assertEqual(self.atendimento.status_atendimento, Atendimento.StatusAtendimento.ENCAMINHADO_PARA_CHAMADO)
        self.assertEqual(self.atendimento.nome, nome_antes)
        self.assertEqual(self.atendimento.email, email_antes)
        self.assertEqual(self.atendimento.mensagens.count(), mensagens_antes)

    def test_no_chamado_created_as_side_effect_of_other_services(self):
        from ahp.models import Criterio
        from atendimento.services.classification_service import (
            NenhumaVersaoAtivaError,
            ServicePriorityClassificationService,
        )

        Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        try:
            ServicePriorityClassificationService.classify(self.atendimento)
        except NenhumaVersaoAtivaError:
            pass

        self.assertEqual(Chamado.objects.count(), 0)

    def test_falls_back_to_motivo_when_no_messages(self):
        atendimento_sem_mensagens = Atendimento.objects.create(nome="Sem Mensagens", email="sem@test.com")
        chamado = TicketCreationService.create_from_atendimento(atendimento_sem_mensagens, motivo="Motivo generico", user=self.user)
        self.assertEqual(chamado.descricao, "Motivo generico")
