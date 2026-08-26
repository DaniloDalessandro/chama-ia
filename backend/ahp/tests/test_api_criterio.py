from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ahp.models import Criterio

User = get_user_model()


class CriterioApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.atendente = User.objects.create_user(email="at@test.com", password="x", name="At", role="atendente")
        self.cliente = User.objects.create_user(email="cli@test.com", password="x", name="Cli", role="cliente")
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")

    def test_anonymous_cannot_list(self):
        response = self.client.get("/api/v1/ahp/criterios")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_atendente_can_read(self):
        self.client.force_authenticate(self.atendente)
        response = self.client.get("/api/v1/ahp/criterios")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_atendente_cannot_write(self):
        self.client.force_authenticate(self.atendente)
        response = self.client.post("/api/v1/ahp/criterios", {"nome": "Impacto", "codigo": "IMPACTO"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cliente_cannot_read(self):
        self.client.force_authenticate(self.cliente)
        response = self.client.get("/api/v1/ahp/criterios")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post("/api/v1/ahp/criterios", {"nome": "Impacto", "codigo": "IMPACTO"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["criado_por"], self.admin.id)

    def test_delete_performs_soft_delete_not_hard_delete(self):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/ahp/criterios/{self.criterio.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Criterio.objects.filter(pk=self.criterio.pk).exists())
        self.assertTrue(Criterio.all_objects.filter(pk=self.criterio.pk).exists())

    def test_inativar_action(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/v1/ahp/criterios/{self.criterio.id}/inativar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.criterio.refresh_from_db()
        self.assertFalse(self.criterio.ativo)

    def test_duplicar_action_copies_active_intensidades(self):
        from ahp.models import Intensidade

        Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/v1/ahp/criterios/{self.criterio.id}/duplicar")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        clone = Criterio.all_objects.get(id=response.data["id"])
        self.assertFalse(clone.ativo)
        self.assertEqual(clone.intensidades.count(), 1)
