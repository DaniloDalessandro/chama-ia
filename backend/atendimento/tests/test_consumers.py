from unittest.mock import patch

from channels.auth import AuthMiddlewareStack
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from atendimento.models import Atendimento, MensagemAtendimento
from atendimento.routing import websocket_urlpatterns
from core.channels_auth import JWTAuthMiddleware

User = get_user_model()

application = JWTAuthMiddleware(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)))

# Redis nao esta disponivel no ambiente local -- usa o channel layer em
# memoria (mesmo padrao recomendado pelos docs do Channels para testes).
_IN_MEMORY_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def _ws_path(atendimento_id, token):
    return f"/ws/atendimento/{atendimento_id}/?token={token}"


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_CHANNEL_LAYERS)
class AtendimentoChatConsumerConnectTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        self.cliente_user = User.objects.create_user(email="cliente@test.com", password="x", name="Cliente", role="cliente")
        # gerados no setUp (sincrono) -- RefreshToken.for_user() grava
        # OutstandingToken no banco, o que levantaria SynchronousOnlyOperation
        # se chamado direto de dentro de um metodo de teste async.
        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)
        self.cliente_token = str(RefreshToken.for_user(self.cliente_user).access_token)

    async def test_anonymous_connect_with_valid_token_accepted(self):
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, self.atendimento.session_token))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        envelope = await communicator.receive_json_from()
        self.assertEqual(envelope["type"], "connection_established")
        self.assertEqual(envelope["atendimento"]["id"], self.atendimento.id)

        await communicator.disconnect()

    async def test_anonymous_connect_with_invalid_token_rejected(self):
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, "00000000-0000-0000-0000-000000000000"))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_anonymous_connect_with_missing_token_rejected(self):
        communicator = WebsocketCommunicator(application, f"/ws/atendimento/{self.atendimento.id}/")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_staff_connect_with_valid_admin_jwt_accepted(self):
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, self.admin_token))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_non_staff_authenticated_user_rejected(self):
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, self.cliente_token))
        connected, _ = await communicator.connect()
        self.assertFalse(connected)


@override_settings(CHANNEL_LAYERS=_IN_MEMORY_CHANNEL_LAYERS)
class AtendimentoChatConsumerMessagingTests(TestCase):
    def setUp(self):
        self.atendimento = Atendimento.objects.create(nome="Cliente", email="c@test.com")
        self.admin = User.objects.create_user(email="admin@test.com", password="x", name="Admin", role="admin")
        # gerado no setUp (sincrono) -- RefreshToken.for_user() grava OutstandingToken
        # no banco, o que levantaria SynchronousOnlyOperation se chamado direto
        # de dentro de um metodo de teste async.
        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)

    async def _connect_anonimo(self):
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, self.atendimento.session_token))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await self._drain_ate(communicator, "connection_established")
        return communicator

    async def _connect_staff(self):
        """
        A conexao de staff sempre recebe DOIS envelopes, nesta ordem
        deterministica: `connection_established` (enviado direto, dentro de
        connect()) e, so depois que connect() retorna e o loop de despacho do
        consumer volta a processar eventos do channel layer, `staff_joined`
        (group_send, que inclui o proprio remetente que acabou de entrar no
        grupo) -- consome os dois antes de devolver o comunicador.
        """
        communicator = WebsocketCommunicator(application, _ws_path(self.atendimento.id, self.admin_token))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await self._drain_ate(communicator, "connection_established")
        await self._drain_ate(communicator, "staff_joined")
        return communicator

    @staticmethod
    async def _drain_ate(communicator, tipo_esperado, max_tentativas=5):
        for _ in range(max_tentativas):
            envelope = await communicator.receive_json_from()
            if envelope.get("type") == tipo_esperado:
                return envelope
        raise AssertionError(f"Envelope do tipo '{tipo_esperado}' nao recebido apos {max_tentativas} tentativas.")

    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    async def test_client_send_message_persists_and_triggers_ai_task(self, mock_delay):
        communicator = await self._connect_anonimo()

        await communicator.send_json_to({"action": "send_message", "conteudo": "Preciso de ajuda"})
        envelope = await communicator.receive_json_from()

        self.assertEqual(envelope["type"], "chat_message")
        self.assertEqual(envelope["mensagem"]["remetente_tipo"], MensagemAtendimento.RemetenteTipo.CLIENTE)
        self.assertEqual(envelope["mensagem"]["conteudo"], "Preciso de ajuda")

        mock_delay.assert_called_once()
        self.assertEqual(mock_delay.call_args.args[0], self.atendimento.id)

        await communicator.disconnect()

    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    async def test_staff_send_message_persists_but_never_triggers_ai_task(self, mock_delay):
        communicator = await self._connect_staff()

        await communicator.send_json_to({"action": "send_message", "conteudo": "Ja estou verificando"})
        envelope = await communicator.receive_json_from()

        self.assertEqual(envelope["mensagem"]["remetente_tipo"], MensagemAtendimento.RemetenteTipo.ATENDENTE)
        mock_delay.assert_not_called()

        await communicator.disconnect()

    async def test_ping_pong(self):
        communicator = await self._connect_anonimo()

        await communicator.send_json_to({"action": "ping", "timestamp": 123})
        envelope = await communicator.receive_json_from()

        self.assertEqual(envelope, {"type": "pong", "timestamp": 123})
        await communicator.disconnect()

    async def test_typing_broadcasts_to_other_connected_socket(self):
        cliente = await self._connect_anonimo()
        staff = await self._connect_staff()
        # o cliente (ja conectado antes) recebe o broadcast staff_joined
        # disparado quando o staff entra no grupo -- drena antes de seguir.
        await cliente.receive_json_from()

        await cliente.send_json_to({"action": "typing"})
        envelope = await staff.receive_json_from()

        self.assertEqual(envelope["type"], "typing")
        self.assertEqual(envelope["remetente_tipo"], "cliente")

        await cliente.disconnect()
        await staff.disconnect()

    @patch("atendimento.tasks.analisar_atendimento_ia_task.delay")
    async def test_two_communicators_both_receive_broadcast(self, mock_delay):
        cliente = await self._connect_anonimo()
        staff = await self._connect_staff()
        await cliente.receive_json_from()  # staff_joined, ainda pendente na fila do cliente

        await cliente.send_json_to({"action": "send_message", "conteudo": "Ola"})

        env_cliente = await cliente.receive_json_from()
        env_staff = await staff.receive_json_from()

        self.assertEqual(env_cliente["type"], "chat_message")
        self.assertEqual(env_staff["type"], "chat_message")
        self.assertEqual(env_cliente["mensagem"]["id"], env_staff["mensagem"]["id"])

        await cliente.disconnect()
        await staff.disconnect()

    async def test_empty_message_returns_error_without_persisting(self):
        communicator = await self._connect_anonimo()

        await communicator.send_json_to({"action": "send_message", "conteudo": "   "})
        envelope = await communicator.receive_json_from()

        self.assertEqual(envelope["type"], "error")
        await communicator.disconnect()

    async def test_unknown_action_returns_error(self):
        communicator = await self._connect_anonimo()
        await communicator.send_json_to({"action": "bogus"})
        envelope = await communicator.receive_json_from()
        self.assertEqual(envelope["type"], "error")
        await communicator.disconnect()
