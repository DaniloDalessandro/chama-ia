"""
AtendimentoChatConsumer: chat em tempo real de um atendimento, suportando
dois caminhos de identidade distintos numa unica classe (convergem no mesmo
comportamento pos-conexao: mesmo grupo, mesmo envelope de mensagens):

- Cliente anonimo: `?token=<session_token>` batendo com o `atendimento_id`
  da URL (`Atendimento.session_token`, UUID, nunca o pk numerico).
- Atendente autenticado: `?token=<JWT>` resolvido para um usuario com
  `role` admin/atendente por `core.channels_auth.JWTAuthMiddleware` (que
  roda antes deste consumer, por fora do AuthMiddlewareStack padrao).

Toda mensagem enviada pelo cliente (nao pelo atendente) dispara
`analisar_atendimento_ia_task` -- resolve o TODO(Fase 2) de reprocessar a
analise a cada nova mensagem.
"""

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class AtendimentoChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.atendimento_id = self.scope["url_route"]["kwargs"]["atendimento_id"]
        token = parse_qs(self.scope.get("query_string", b"").decode()).get("token", [None])[0]

        self.is_staff_connection = False
        self.user = None
        self.atendimento = None

        scope_user = self.scope.get("user")
        if scope_user is not None and not isinstance(scope_user, AnonymousUser) and getattr(scope_user, "is_authenticated", False):
            role = await self._get_user_role(scope_user)
            if role in ("admin", "atendente"):
                self.is_staff_connection = True
                self.user = scope_user
                self.atendimento = await self._get_atendimento(self.atendimento_id)

        if not self.is_staff_connection:
            if not token:
                await self.close(code=4001)
                return
            self.atendimento = await self._lookup_atendimento_by_token(self.atendimento_id, token)
            if self.atendimento is None:
                await self.close(code=4001)
                return

        if self.atendimento is None:
            await self.close(code=4004)
            return

        self.group_name = f"atendimento_chat_{self.atendimento_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        if self.is_staff_connection:
            await self.channel_layer.group_send(self.group_name, {
                "type": "staff_joined",
                "atendente": {"id": self.user.id, "name": self.user.name},
            })

        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "atendimento": {
                "id": self.atendimento.id,
                "status_atendimento": self.atendimento.status_atendimento,
                "analise_ia_status": self.atendimento.analise_ia_status,
                "prioridade": self.atendimento.prioridade,
            },
        }))

    async def disconnect(self, close_code):
        if getattr(self, "group_name", None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            if self.is_staff_connection and self.user:
                await self.channel_layer.group_send(self.group_name, {
                    "type": "staff_left",
                    "atendente": {"id": self.user.id, "name": self.user.name},
                })

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (TypeError, ValueError):
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
            return

        action = data.get("action")
        if action == "send_message":
            await self._handle_send_message(data)
        elif action == "typing":
            await self._handle_typing()
        elif action == "ping":
            await self.send(text_data=json.dumps({"type": "pong", "timestamp": data.get("timestamp")}))
        else:
            await self.send(text_data=json.dumps({"type": "error", "message": f"Unknown action: {action}"}))

    async def _handle_send_message(self, data):
        conteudo = (data.get("conteudo") or "").strip()
        if not conteudo:
            await self.send(text_data=json.dumps({"type": "error", "message": "conteudo vazio"}))
            return

        from .models import MensagemAtendimento

        remetente_tipo = (
            MensagemAtendimento.RemetenteTipo.ATENDENTE if self.is_staff_connection
            else MensagemAtendimento.RemetenteTipo.CLIENTE
        )
        mensagem_data = await self._criar_mensagem(remetente_tipo, conteudo)

        await self.channel_layer.group_send(self.group_name, {"type": "chat_message", "mensagem": mensagem_data})

        if remetente_tipo == MensagemAtendimento.RemetenteTipo.CLIENTE:
            try:
                from .tasks import analisar_atendimento_ia_task
                analisar_atendimento_ia_task.delay(self.atendimento.id, mensagem_id=mensagem_data["id"])
            except Exception:
                logger.warning("Falha ao disparar analisar_atendimento_ia_task apos mensagem via WS.", exc_info=True)

    async def _handle_typing(self):
        await self.channel_layer.group_send(self.group_name, {
            "type": "typing_indicator",
            "remetente_tipo": "atendente" if self.is_staff_connection else "cliente",
            "sender_label": "Atendente" if self.is_staff_connection else "Cliente",
        })

    # --- Handlers de grupo (o nome do metodo deve bater com "type" do group_send) ---

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "chat_message", "mensagem": event["mensagem"]}))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            "type": "typing", "remetente_tipo": event["remetente_tipo"], "sender_label": event["sender_label"],
        }))

    async def staff_joined(self, event):
        await self.send(text_data=json.dumps({"type": "staff_joined", "atendente": event["atendente"]}))

    async def staff_left(self, event):
        await self.send(text_data=json.dumps({"type": "staff_left", "atendente": event["atendente"]}))

    async def analise_status_changed(self, event):
        # Seam para Fase 4 -- nenhum codigo hoje dispara este evento ainda
        # (ver decisao no plano da Fase 3: polling REST e suficiente por ora).
        await self.send(text_data=json.dumps({
            "type": "analise_status_changed",
            "analise_ia_status": event.get("analise_ia_status"),
            "prioridade": event.get("prioridade"),
            "indice_ahp": event.get("indice_ahp"),
        }))

    # --- Helpers de banco ---

    @database_sync_to_async
    def _get_user_role(self, user):
        return getattr(user, "role", None)

    @database_sync_to_async
    def _lookup_atendimento_by_token(self, atendimento_id, token):
        from django.core.exceptions import ValidationError

        from .models import Atendimento
        try:
            return Atendimento.objects.filter(pk=atendimento_id, session_token=token).first()
        except (ValueError, TypeError, ValidationError):
            return None

    @database_sync_to_async
    def _get_atendimento(self, atendimento_id):
        from .models import Atendimento
        return Atendimento.objects.filter(pk=atendimento_id).first()

    @database_sync_to_async
    def _criar_mensagem(self, remetente_tipo, conteudo):
        from .models import MensagemAtendimento
        from .serializers import MensagemAtendimentoSerializer

        mensagem = MensagemAtendimento.objects.create(
            atendimento=self.atendimento, remetente_tipo=remetente_tipo, conteudo=conteudo,
        )
        return MensagemAtendimentoSerializer(mensagem).data
