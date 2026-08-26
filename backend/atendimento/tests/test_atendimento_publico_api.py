from unittest.mock import patch

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from atendimento.models import Atendimento, MensagemAtendimento
from atendimento.throttling import AtendimentoPublicoRateThrottle


class AtendimentoPublicoCreateApiTests(APITestCase):
    def setUp(self):
        cache.clear()  # throttle usa cache global -- isola cada teste do rate limit dos outros

    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    def test_creates_atendimento_and_returns_session_token(self, mock_delay):
        response = self.client.post(
            "/api/v1/atendimento/publico/",
            {"nome": "Cliente Anonimo", "email": "anon@test.com", "mensagem_inicial": "Preciso de ajuda"},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn("session_token", response.data)

        atendimento = Atendimento.objects.get(id=response.data["id"])
        self.assertEqual(atendimento.origem, Atendimento.Origem.CHAT)
        self.assertEqual(atendimento.status_atendimento, Atendimento.StatusAtendimento.AGUARDANDO)
        self.assertEqual(atendimento.mensagens.count(), 1)
        self.assertEqual(atendimento.mensagens.first().remetente_tipo, MensagemAtendimento.RemetenteTipo.CLIENTE)
        mock_delay.assert_called_once_with(atendimento.id)

    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    def test_mensagem_inicial_is_optional(self, mock_delay):
        response = self.client.post("/api/v1/atendimento/publico/", {"nome": "Cliente", "email": "c@test.com"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        atendimento = Atendimento.objects.get(id=response.data["id"])
        self.assertEqual(atendimento.mensagens.count(), 0)

    def test_missing_required_fields_returns_400(self):
        response = self.client.post("/api/v1/atendimento/publico/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_set_origem(self):
        with patch("atendimento.tasks.analisar_atendimento_ia_task.delay"):
            response = self.client.post(
                "/api/v1/atendimento/publico/",
                {"nome": "X", "email": "x@test.com", "origem": "email"},
            )
        atendimento = Atendimento.objects.get(id=response.data["id"])
        self.assertEqual(atendimento.origem, Atendimento.Origem.CHAT)

    @patch.object(AtendimentoPublicoRateThrottle, "rate", "2/min")
    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    def test_rate_limiting(self, mock_delay):
        for _ in range(2):
            response = self.client.post("/api/v1/atendimento/publico/", {"nome": "X", "email": "x@test.com"})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post("/api/v1/atendimento/publico/", {"nome": "X", "email": "x@test.com"})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AtendimentoPublicoDetailApiTests(APITestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")

    def test_lookup_by_valid_token(self):
        response = self.client.get(f"/api/v1/atendimento/publico/{self.atendimento.session_token}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.atendimento.id)
        self.assertIsNone(response.data["sla"])

    def test_lookup_by_random_token_404(self):
        response = self.client.get("/api/v1/atendimento/publico/00000000-0000-0000-0000-000000000000/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_response_never_leaks_numeric_pk_guessing_surface(self):
        # a view nunca aceita lookup por pk -- so por token
        response = self.client.get(f"/api/v1/atendimento/publico/{self.atendimento.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AtendimentoPublicoMensagensApiTests(APITestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=MensagemAtendimento.RemetenteTipo.CLIENTE, conteudo="Ola"
        )

    def test_lists_mensagens_by_token(self):
        response = self.client.get(f"/api/v1/atendimento/publico/{self.atendimento.session_token}/mensagens/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_invalid_token_404(self):
        response = self.client.get("/api/v1/atendimento/publico/00000000-0000-0000-0000-000000000000/mensagens/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
