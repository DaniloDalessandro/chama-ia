"""
WebSocket Consumer para notificacoes em tempo real.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer para notificacoes em tempo real via WebSocket.

    Cada usuario tem seu proprio grupo: notifications_user_{user.id}
    """

    async def connect(self):
        """
        Chamado quando o WebSocket e conectado.
        Autentica o usuario e adiciona ao grupo pessoal.
        """
        # Obter usuario da sessao
        self.user = self.scope.get("user")

        # Verificar autenticacao
        if not self.user or isinstance(self.user, AnonymousUser):
            logger.warning("Tentativa de conexao WebSocket sem autenticacao")
            await self.close()
            return

        # Nome do grupo pessoal do usuario
        self.group_name = f"notifications_user_{self.user.id}"

        # Adicionar ao grupo
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Aceitar conexao
        await self.accept()

        logger.info(
            f"WebSocket conectado para usuario {self.user.username} "
            f"no grupo {self.group_name}"
        )

        # Enviar mensagem de confirmacao
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "WebSocket connected successfully"
        }))

    async def disconnect(self, close_code):
        """
        Chamado quando o WebSocket e desconectado.
        Remove o usuario do grupo.
        """
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

            logger.info(
                f"WebSocket desconectado para usuario {self.user.username} "
                f"(close_code: {close_code})"
            )

    async def receive(self, text_data):
        """
        Chamado quando o WebSocket recebe uma mensagem do cliente.

        Suporta os seguintes comandos:
        - {"action": "ping"} -> Responde com pong
        - {"action": "mark_read", "notification_id": "..."} -> Marca notificacao como lida
        - {"action": "mark_all_read"} -> Marca todas como lidas
        """
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "ping":
                await self.send(text_data=json.dumps({
                    "type": "pong",
                    "timestamp": data.get("timestamp")
                }))

            elif action == "mark_read":
                notification_id = data.get("notification_id")
                if notification_id:
                    success = await self.mark_notification_read(notification_id)
                    await self.send(text_data=json.dumps({
                        "type": "mark_read_response",
                        "notification_id": notification_id,
                        "success": success
                    }))

            elif action == "mark_all_read":
                count = await self.mark_all_notifications_read()
                await self.send(text_data=json.dumps({
                    "type": "mark_all_read_response",
                    "count": count,
                    "success": True
                }))

            else:
                logger.warning(f"Acao desconhecida recebida: {action}")
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                }))

        except json.JSONDecodeError:
            logger.error("Erro ao decodificar JSON do WebSocket")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Invalid JSON"
            }))
        except Exception as e:
            logger.error(f"Erro ao processar mensagem WebSocket: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": str(e)
            }))

    async def notification_send(self, event):
        """
        Chamado quando uma notificacao e enviada para o grupo.
        Este metodo e chamado pelo channel_layer.group_send().

        Args:
            event: Dict com os dados da notificacao
        """
        notification = event.get("notification")

        # Enviar notificacao para o WebSocket
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": notification
        }))

        logger.debug(
            f"Notificacao enviada via WebSocket para {self.user.username}: "
            f"{notification.get('title')}"
        )

    @database_sync_to_async
    def mark_notification_read(self, notification_id: str) -> bool:
        """
        Marca uma notificacao como lida.

        Args:
            notification_id: ID da notificacao

        Returns:
            bool: True se marcada com sucesso
        """
        from chamados.services.notification_service import NotificationService

        return NotificationService.mark_as_read(notification_id, self.user)

    @database_sync_to_async
    def mark_all_notifications_read(self) -> int:
        """
        Marca todas as notificacoes do usuario como lidas.

        Returns:
            int: Quantidade de notificacoes marcadas
        """
        from chamados.services.notification_service import NotificationService

        return NotificationService.mark_all_as_read(self.user)
