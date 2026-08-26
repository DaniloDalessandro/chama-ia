from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from atendimento.models import Atendimento

User = get_user_model()


class FilaApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.cliente_user = User.objects.create_user(email="cliente@test.com", password="x", name="Cliente", role="cliente")
        Atendimento.objects.create(nome="A", email="a@test.com", prioridade=Atendimento.Prioridade.P1, indice_ahp=90)
        Atendimento.objects.create(nome="B", email="b@test.com", prioridade=Atendimento.Prioridade.P3)
        Atendimento.objects.create(
            nome="Resolvido", email="r@test.com", prioridade=Atendimento.Prioridade.P1,
            status_atendimento=Atendimento.StatusAtendimento.RESOLVIDO,
        )

    def test_admin_sees_ordered_fila(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/atendimento/atendimentos/fila")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # o resolvido nao aparece
        self.assertEqual(response.data[0]["nome"], "A")  # P1 antes de P3

    def test_fila_card_has_section_27_fields_and_sla_is_null(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/atendimento/atendimentos/fila")

        card = response.data[0]
        for campo in [
            "id", "nome", "cliente", "assunto", "resumo", "servico_afetado", "prioridade", "indice_ahp",
            "analise_ia_status", "tempo_espera_minutos", "sla", "atendente", "anexos_count",
            "dados_ausentes", "regra_critica_confirmada", "status_atendimento", "criado_em",
        ]:
            self.assertIn(campo, card)
        self.assertIsNone(card["sla"])

    def test_cliente_role_forbidden(self):
        self.client.force_authenticate(self.cliente_user)
        response = self.client.get("/api/v1/atendimento/atendimentos/fila")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_unauthorized(self):
        response = self.client.get("/api/v1/atendimento/atendimentos/fila")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
