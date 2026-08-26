from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from atendimento.models import Atendimento, MensagemAtendimento
from atendimento.serializers import AtendimentoDetailPublicSerializer
from atendimento.services.ticket_creation_service import TicketCreationService

User = get_user_model()


class DetalheApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE, conteudo="Ola"
        )

    def test_staff_sees_full_detail_without_chamado_relacionado(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/v1/atendimento/atendimentos/{self.atendimento.id}/detalhe")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for chave in ["atendimento", "conversa", "anexos", "avaliacoes_criterios", "auditoria_mais_recente", "regra_critica", "revisoes_humanas", "chamado_relacionado"]:
            self.assertIn(chave, response.data)
        self.assertEqual(len(response.data["conversa"]), 1)
        self.assertIsNone(response.data["chamado_relacionado"])

    def test_staff_sees_chamado_relacionado_when_present(self):
        chamado = TicketCreationService.create_from_atendimento(self.atendimento, motivo="nao resolvido", user=self.admin)

        self.client.force_authenticate(self.admin)
        response = self.client.get(f"/api/v1/atendimento/atendimentos/{self.atendimento.id}/detalhe")

        self.assertIsNotNone(response.data["chamado_relacionado"])
        self.assertEqual(response.data["chamado_relacionado"]["id"], chamado.id)
        self.assertEqual(response.data["chamado_relacionado"]["protocolo"], chamado.protocolo)

    def test_public_serializer_never_leaks_ahp_internals(self):
        data = AtendimentoDetailPublicSerializer(self.atendimento).data
        chaves_proibidas = {
            "pesos_criterios", "versao_matriz_criterios", "versao_matriz_intensidades",
            "lambda_max", "ci", "cr", "prioridades_locais", "auditoria_mais_recente", "regra_critica",
        }
        self.assertEqual(set(data.keys()) & chaves_proibidas, set())
        self.assertIsNone(data["sla"])
