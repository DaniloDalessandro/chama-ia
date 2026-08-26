from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ahp.models import (
    CODIGO_IMPACTO_NO_CLIENTE,
    CODIGO_SENTIMENTO_DO_CLIENTE,
    CODIGO_TEMPO_DE_ESPERA,
    CODIGO_URGENCIA,
    Criterio,
    FaixaTempoEspera,
    Intensidade,
    VersaoAHP,
)

User = get_user_model()


class VersaoAHPApiTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.client.force_authenticate(self.admin)

        self.criterios = {}
        self.intensidades = {}
        for ordem, codigo in enumerate(
            [CODIGO_URGENCIA, CODIGO_IMPACTO_NO_CLIENTE, CODIGO_SENTIMENTO_DO_CLIENTE, CODIGO_TEMPO_DE_ESPERA], start=1
        ):
            criterio = Criterio.objects.create(nome=codigo.title(), codigo=codigo, ordem=ordem)
            self.criterios[codigo] = criterio
            Intensidade.objects.create(criterio=criterio, nome="Ausente", codigo=Intensidade.Codigo.AUSENTE, ordem=1)
            baixa = Intensidade.objects.create(criterio=criterio, nome="Baixa", codigo=Intensidade.Codigo.BAIXA, ordem=2)
            moderada = Intensidade.objects.create(criterio=criterio, nome="Moderada", codigo=Intensidade.Codigo.MODERADA, ordem=3)
            critica = Intensidade.objects.create(criterio=criterio, nome="Critica", codigo=Intensidade.Codigo.CRITICA, ordem=4)
            Intensidade.objects.create(criterio=criterio, nome="Inconclusiva", codigo=Intensidade.Codigo.INCONCLUSIVA, ordem=5)
            self.intensidades[codigo] = [baixa, moderada, critica]

        criterio_tempo = self.criterios[CODIGO_TEMPO_DE_ESPERA]
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=0, minutos_max=5, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][0], ordem=1)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=5, minutos_max=15, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][1], ordem=2)
        FaixaTempoEspera.objects.create(criterio=criterio_tempo, minutos_min=15, minutos_max=None, intensidade=self.intensidades[CODIGO_TEMPO_DE_ESPERA][2], ordem=3)

    def _create_versao(self):
        response = self.client.post("/api/v1/ahp/versoes-ahp", {"descricao": "v1"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

    def _submit_valid_comparisons(self, versao_id):
        ordenados = [
            self.criterios[CODIGO_URGENCIA], self.criterios[CODIGO_IMPACTO_NO_CLIENTE],
            self.criterios[CODIGO_SENTIMENTO_DO_CLIENTE], self.criterios[CODIGO_TEMPO_DE_ESPERA],
        ]
        payload = [
            {"item_linha_id": ordenados[0].id, "item_coluna_id": ordenados[1].id, "valor_saaty": 2.0},
            {"item_linha_id": ordenados[0].id, "item_coluna_id": ordenados[2].id, "valor_saaty": 4.0},
            {"item_linha_id": ordenados[0].id, "item_coluna_id": ordenados[3].id, "valor_saaty": 8.0},
            {"item_linha_id": ordenados[1].id, "item_coluna_id": ordenados[2].id, "valor_saaty": 2.0},
            {"item_linha_id": ordenados[1].id, "item_coluna_id": ordenados[3].id, "valor_saaty": 4.0},
            {"item_linha_id": ordenados[2].id, "item_coluna_id": ordenados[3].id, "valor_saaty": 2.0},
        ]
        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/comparacoes-criterios", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        for codigo, itens in self.intensidades.items():
            payload = [
                {"item_linha_id": itens[0].id, "item_coluna_id": itens[1].id, "valor_saaty": 2.0},
                {"item_linha_id": itens[0].id, "item_coluna_id": itens[2].id, "valor_saaty": 4.0},
                {"item_linha_id": itens[1].id, "item_coluna_id": itens[2].id, "valor_saaty": 2.0},
            ]
            response = self.client.post(
                f"/api/v1/ahp/versoes-ahp/{versao_id}/comparacoes-intensidades/{codigo}", payload, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_full_bulk_submission_validate_and_activate(self):
        versao_id = self._create_versao()
        self._submit_valid_comparisons(versao_id)

        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/validar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valido"])
        self.assertEqual(response.data["erros"], [])

        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/ativar")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["estado"], VersaoAHP.Estado.ATIVA)

        response = self.client.get("/api/v1/ahp/versoes-ahp/ativa")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], versao_id)

    def test_reversed_pair_order_is_normalized_via_reciprocal(self):
        versao_id = self._create_versao()
        u = self.criterios[CODIGO_URGENCIA]
        i = self.criterios[CODIGO_IMPACTO_NO_CLIENTE]
        # envia (coluna, linha) fora de ordem -- o backend deve normalizar via reciproco
        payload = [{"item_linha_id": i.id, "item_coluna_id": u.id, "valor_saaty": 0.5}]
        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/comparacoes-criterios", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_ativar_reports_inconsistent_without_touching_previous_active(self):
        versao1_id = self._create_versao()
        self._submit_valid_comparisons(versao1_id)
        self.client.post(f"/api/v1/ahp/versoes-ahp/{versao1_id}/ativar")

        versao2_id = self._create_versao()
        self._submit_valid_comparisons(versao2_id)
        # sobrescreve a matriz de intensidades de URGENCIA com uma versao inconsistente
        itens = self.intensidades[CODIGO_URGENCIA]
        payload = [
            {"item_linha_id": itens[0].id, "item_coluna_id": itens[1].id, "valor_saaty": 5.0},
            {"item_linha_id": itens[0].id, "item_coluna_id": itens[2].id, "valor_saaty": 6.0},
            {"item_linha_id": itens[1].id, "item_coluna_id": itens[2].id, "valor_saaty": 4.0},
        ]
        self.client.post(
            f"/api/v1/ahp/versoes-ahp/{versao2_id}/comparacoes-intensidades/{CODIGO_URGENCIA}", payload, format="json"
        )

        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao2_id}/ativar")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data["estado"], VersaoAHP.Estado.INCONSISTENTE)

        response = self.client.get("/api/v1/ahp/versoes-ahp/ativa")
        self.assertEqual(response.data["id"], versao1_id)

    def test_cannot_edit_comparisons_after_activation(self):
        versao_id = self._create_versao()
        self._submit_valid_comparisons(versao_id)
        self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/ativar")

        payload = [{"item_linha_id": self.criterios[CODIGO_URGENCIA].id, "item_coluna_id": self.criterios[CODIGO_IMPACTO_NO_CLIENTE].id, "valor_saaty": 3.0}]
        response = self.client.post(f"/api/v1/ahp/versoes-ahp/{versao_id}/comparacoes-criterios", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_atendente_cannot_create_version(self):
        atendente = User.objects.create_user(email="at@test.com", password="x", name="At", role="atendente")
        self.client.force_authenticate(atendente)
        response = self.client.post("/api/v1/ahp/versoes-ahp", {"descricao": "v1"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
