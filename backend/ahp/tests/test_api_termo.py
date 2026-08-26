from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ahp.models import Criterio, Intensidade, Termo

User = get_user_model()


class TermoApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.atendente = User.objects.create_user(email="at@test.com", password="x", name="At", role="atendente")
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")
        self.intensidade = Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)
        self.termo = Termo.objects.create(criterio=self.criterio, termo="vence hoje", intensidade_base=self.intensidade)

    def test_admin_can_create_termo(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "criterio": self.criterio.id,
            "termo": "prazo legal",
            "intensidade_base": self.intensidade.id,
        }
        response = self.client.post("/api/v1/ahp/termos", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status_aprovacao"], Termo.StatusAprovacao.APROVADO)

    def test_intensidade_base_must_belong_to_same_criterio(self):
        outro_criterio = Criterio.objects.create(nome="Impacto", codigo="IMPACTO_NO_CLIENTE")
        outra_intensidade = Intensidade.objects.create(
            criterio=outro_criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA
        )
        self.client.force_authenticate(self.admin)
        payload = {"criterio": self.criterio.id, "termo": "x", "intensidade_base": outra_intensidade.id}
        response = self.client.post("/api/v1/ahp/termos", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_atendente_cannot_approve(self):
        self.client.force_authenticate(self.atendente)
        response = self.client.post(f"/api/v1/ahp/termos/{self.termo.id}/aprovar")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_reject_termo(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/ahp/termos/{self.termo.id}/rejeitar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.termo.refresh_from_db()
        self.assertEqual(self.termo.status_aprovacao, Termo.StatusAprovacao.REJEITADO)

    def test_filter_by_status_aprovacao(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/ahp/termos", {"status_aprovacao": "aprovado"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
