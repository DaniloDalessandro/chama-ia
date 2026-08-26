from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ahp.models import Criterio, Intensidade

User = get_user_model()


class IntensidadeApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.criterio = Criterio.objects.create(nome="Urgencia", codigo="URGENCIA")

    def test_admin_can_create_intensidade(self):
        self.client.force_authenticate(self.admin)
        payload = {"criterio": self.criterio.id, "nome": "Critica", "codigo": Intensidade.Codigo.CRITICA}
        response = self.client.post("/api/v1/ahp/intensidades", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_codigo_for_same_criterio_is_rejected(self):
        Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)
        self.client.force_authenticate(self.admin)
        payload = {"criterio": self.criterio.id, "nome": "Alta de novo", "codigo": Intensidade.Codigo.ALTA}
        response = self.client.post("/api/v1/ahp/intensidades", payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_performs_soft_delete(self):
        intensidade = Intensidade.objects.create(criterio=self.criterio, nome="Alta", codigo=Intensidade.Codigo.ALTA)
        self.client.force_authenticate(self.admin)
        response = self.client.delete(f"/api/v1/ahp/intensidades/{intensidade.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Intensidade.objects.filter(pk=intensidade.pk).exists())
        self.assertTrue(Intensidade.all_objects.filter(pk=intensidade.pk).exists())
