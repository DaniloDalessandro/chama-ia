"""
Servico para gerenciamento de notificacoes em tempo real.
Responsavel por criar notificacoes e fazer broadcast via WebSocket.
"""

import logging
from typing import List, Optional
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from chamados.models import Notification, Chamado

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Servico centralizado para gerenciamento de notificacoes."""

    @staticmethod
    def create_and_broadcast(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        chamado: Optional[Chamado] = None
    ) -> Notification:
        """
        Cria uma notificacao no banco de dados e faz broadcast via WebSocket.

        Args:
            user: Usuario que recebera a notificacao
            notification_type: Tipo da notificacao (usar Notification.NotificationType)
            title: Titulo da notificacao
            message: Mensagem detalhada
            chamado: Chamado relacionado (opcional)

        Returns:
            Notification: Instancia da notificacao criada
        """
        # Criar notificacao no banco
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            chamado=chamado
        )

        logger.info(
            f"Notificacao criada: {notification.id} para usuario {user.username}"
        )

        # Fazer broadcast via WebSocket
        NotificationService._broadcast_to_user(user, notification)

        return notification

    @staticmethod
    def _broadcast_to_user(user: User, notification: Notification):
        """
        Envia notificacao via WebSocket para o usuario.

        Args:
            user: Usuario que recebera a notificacao
            notification: Instancia da notificacao
        """
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("Channel layer nao configurado. WebSocket desabilitado.")
            return

        group_name = f"notifications_user_{user.id}"

        # Preparar payload
        payload = {
            "type": "notification_send",
            "notification": {
                "id": str(notification.id),
                "type": notification.notification_type,
                "title": notification.title,
                "message": notification.message,
                "chamado_id": notification.chamado_id,
                "chamado_protocolo": notification.chamado.protocolo if notification.chamado else None,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
        }

        try:
            async_to_sync(channel_layer.group_send)(group_name, payload)
            logger.info(f"Notificacao enviada via WebSocket para {user.username}")
        except Exception as e:
            logger.error(f"Erro ao enviar notificacao via WebSocket: {e}")

    @staticmethod
    def notify_chamado_created(chamado: Chamado):
        """
        Notifica todos os admins quando um novo chamado e criado.

        Args:
            chamado: Instancia do chamado criado
        """
        # Buscar todos os admins
        admins = User.objects.filter(is_staff=True, is_active=True)

        for admin in admins:
            NotificationService.create_and_broadcast(
                user=admin,
                notification_type=Notification.NotificationType.CHAMADO_CREATED,
                title=f"Novo Chamado #{chamado.protocolo}",
                message=f"Um novo chamado foi criado: {chamado.assunto}",
                chamado=chamado
            )

        logger.info(
            f"Notificacao de novo chamado enviada para {admins.count()} admins"
        )

    @staticmethod
    def notify_chamado_assigned(chamado: Chamado, atendente: User):
        """
        Notifica o atendente quando um chamado e atribuido a ele.

        Args:
            chamado: Instancia do chamado
            atendente: Usuario atendente atribuido
        """
        if not atendente or not atendente.is_active:
            return

        NotificationService.create_and_broadcast(
            user=atendente,
            notification_type=Notification.NotificationType.CHAMADO_ASSIGNED,
            title=f"Chamado Atribuido #{chamado.protocolo}",
            message=f"O chamado '{chamado.assunto}' foi atribuido a voce.",
            chamado=chamado
        )

        logger.info(
            f"Notificacao de atribuicao enviada para {atendente.username}"
        )

    @staticmethod
    def notify_priority_changed(chamado: Chamado):
        """
        Notifica admins e atendente quando prioridade muda para URGENTE.

        Args:
            chamado: Instancia do chamado
        """
        if chamado.prioridade != Chamado.Prioridade.URGENTE:
            return

        # Notificar admins
        admins = User.objects.filter(is_staff=True, is_active=True)
        for admin in admins:
            NotificationService.create_and_broadcast(
                user=admin,
                notification_type=Notification.NotificationType.PRIORITY_URGENT,
                title=f"Prioridade URGENTE - #{chamado.protocolo}",
                message=f"O chamado '{chamado.assunto}' foi marcado como URGENTE.",
                chamado=chamado
            )

        # Notificar atendente atribuido (se houver)
        if chamado.atendente and chamado.atendente.is_active:
            NotificationService.create_and_broadcast(
                user=chamado.atendente,
                notification_type=Notification.NotificationType.PRIORITY_URGENT,
                title=f"Prioridade URGENTE - #{chamado.protocolo}",
                message=f"O chamado '{chamado.assunto}' foi marcado como URGENTE.",
                chamado=chamado
            )

        logger.info(
            f"Notificacao de prioridade urgente enviada para chamado {chamado.protocolo}"
        )

    @staticmethod
    def get_unread_count(user: User) -> int:
        """
        Retorna a quantidade de notificacoes nao lidas do usuario.

        Args:
            user: Usuario

        Returns:
            int: Quantidade de notificacoes nao lidas
        """
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id: str, user: User) -> bool:
        """
        Marca uma notificacao como lida.

        Args:
            notification_id: ID da notificacao
            user: Usuario (para verificar permissao)

        Returns:
            bool: True se marcada com sucesso, False caso contrario
        """
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.mark_as_read()
            logger.info(f"Notificacao {notification_id} marcada como lida")
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notificacao {notification_id} nao encontrada para usuario {user.username}")
            return False

    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """
        Marca todas as notificacoes do usuario como lidas.

        Args:
            user: Usuario

        Returns:
            int: Quantidade de notificacoes marcadas como lidas
        """
        from django.utils import timezone

        count = Notification.objects.filter(
            user=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )

        logger.info(f"{count} notificacoes marcadas como lidas para {user.username}")
        return count
