"""
Servico para gerenciamento e envio de webhooks HTTP.
Suporta Discord, Slack e webhooks customizados.
"""

import logging
import requests
from typing import Dict, Any, List
from django.utils import timezone
from chamados.models import WebhookConfig, WebhookLog, Chamado

logger = logging.getLogger(__name__)


class WebhookService:
    """Servico centralizado para gerenciamento de webhooks."""

    @staticmethod
    def format_discord_payload(chamado: Chamado, event: str) -> Dict[str, Any]:
        """
        Formata payload para webhook do Discord com embed rico.

        Args:
            chamado: Instancia do chamado
            event: Nome do evento (chamado_created, etc)

        Returns:
            Dict: Payload formatado para Discord
        """
        # Cores por prioridade
        color_map = {
            Chamado.Prioridade.BAIXA: 0x95a5a6,      # Cinza
            Chamado.Prioridade.MEDIA: 0x3498db,      # Azul
            Chamado.Prioridade.ALTA: 0xf39c12,       # Laranja
            Chamado.Prioridade.URGENTE: 0xe74c3c,    # Vermelho
        }

        # Titulos por evento
        event_titles = {
            "chamado_created": "🆕 Novo Chamado Criado",
            "chamado_assigned": "👤 Chamado Atribuido",
            "priority_urgent": "🚨 Prioridade URGENTE",
        }

        embed = {
            "title": event_titles.get(event, "Notificacao de Chamado"),
            "description": chamado.assunto,
            "color": color_map.get(chamado.prioridade, 0x95a5a6),
            "fields": [
                {
                    "name": "Protocolo",
                    "value": f"`{chamado.protocolo}`",
                    "inline": True
                },
                {
                    "name": "Tipo",
                    "value": chamado.get_tipo_display(),
                    "inline": True
                },
                {
                    "name": "Prioridade",
                    "value": chamado.get_prioridade_display(),
                    "inline": True
                },
                {
                    "name": "Cliente",
                    "value": chamado.nome,
                    "inline": True
                },
                {
                    "name": "Email",
                    "value": chamado.email,
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": chamado.get_status_display(),
                    "inline": True
                },
            ],
            "timestamp": chamado.created_at.isoformat(),
            "footer": {
                "text": "Chama IA - Sistema de Chamados"
            }
        }

        # Adicionar atendente se atribuido
        if chamado.atendente:
            embed["fields"].append({
                "name": "Atendente",
                "value": chamado.atendente.get_full_name() or chamado.atendente.username,
                "inline": True
            })

        # Adicionar cliente se disponivel
        if chamado.cliente:
            embed["fields"].append({
                "name": "Empresa",
                "value": chamado.cliente.razao_social,
                "inline": True
            })

        return {
            "embeds": [embed]
        }

    @staticmethod
    def format_slack_payload(chamado: Chamado, event: str) -> Dict[str, Any]:
        """
        Formata payload para webhook do Slack com blocks.

        Args:
            chamado: Instancia do chamado
            event: Nome do evento

        Returns:
            Dict: Payload formatado para Slack
        """
        # Emojis por evento
        event_emojis = {
            "chamado_created": ":new:",
            "chamado_assigned": ":bust_in_silhouette:",
            "priority_urgent": ":rotating_light:",
        }

        emoji = event_emojis.get(event, ":bell:")

        # Titulos por evento
        event_titles = {
            "chamado_created": "Novo Chamado Criado",
            "chamado_assigned": "Chamado Atribuido",
            "priority_urgent": "Prioridade URGENTE",
        }

        title = event_titles.get(event, "Notificacao de Chamado")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Protocolo:*\n`{chamado.protocolo}`"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Prioridade:*\n{chamado.get_prioridade_display()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Tipo:*\n{chamado.get_tipo_display()}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{chamado.get_status_display()}"
                    },
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Assunto:*\n{chamado.assunto}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Cliente:*\n{chamado.nome}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Email:*\n{chamado.email}"
                    },
                ]
            },
        ]

        # Adicionar atendente se atribuido
        if chamado.atendente:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Atendente:*\n{chamado.atendente.get_full_name() or chamado.atendente.username}"
                }
            })

        # Adicionar divider
        blocks.append({"type": "divider"})

        # Footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Chama IA | {chamado.created_at.strftime('%d/%m/%Y %H:%M')}"
                }
            ]
        })

        return {"blocks": blocks}

    @staticmethod
    def format_custom_payload(chamado: Chamado, event: str) -> Dict[str, Any]:
        """
        Formata payload generico JSON para webhooks customizados.

        Args:
            chamado: Instancia do chamado
            event: Nome do evento

        Returns:
            Dict: Payload generico JSON
        """
        return {
            "event": event,
            "timestamp": timezone.now().isoformat(),
            "chamado": {
                "protocolo": chamado.protocolo,
                "assunto": chamado.assunto,
                "descricao": chamado.descricao,
                "tipo": chamado.tipo,
                "tipo_display": chamado.get_tipo_display(),
                "prioridade": chamado.prioridade,
                "prioridade_display": chamado.get_prioridade_display(),
                "status": chamado.status,
                "status_display": chamado.get_status_display(),
                "cliente": {
                    "nome": chamado.nome,
                    "email": chamado.email,
                    "telefone": chamado.telefone,
                    "empresa": chamado.cliente.razao_social if chamado.cliente else None,
                },
                "atendente": {
                    "username": chamado.atendente.username if chamado.atendente else None,
                    "nome": chamado.atendente.get_full_name() if chamado.atendente else None,
                } if chamado.atendente else None,
                "created_at": chamado.created_at.isoformat(),
            }
        }

    @staticmethod
    def trigger_webhooks(chamado: Chamado, event: str):
        """
        Dispara todos os webhooks ativos configurados para o evento.
        Envia tasks assincronas via Celery.

        Args:
            chamado: Instancia do chamado
            event: Nome do evento (chamado_created, chamado_assigned, priority_urgent)
        """
        from chamados.tasks import send_webhook_task

        # Buscar webhooks ativos que tem este evento configurado
        webhooks = WebhookConfig.objects.filter(
            is_active=True,
            trigger_events__contains=[event]
        )

        for webhook in webhooks:
            # Disparar task assincrona
            send_webhook_task.delay(
                webhook_id=str(webhook.id),
                chamado_id=chamado.id,
                event=event
            )

        logger.info(
            f"Disparados {webhooks.count()} webhooks para evento '{event}' "
            f"do chamado {chamado.protocolo}"
        )

    @staticmethod
    def send_webhook(webhook: WebhookConfig, chamado: Chamado, event: str) -> Dict[str, Any]:
        """
        Envia webhook HTTP POST com retry.
        Metodo chamado pela task Celery.

        Args:
            webhook: Configuracao do webhook
            chamado: Instancia do chamado
            event: Nome do evento

        Returns:
            Dict: Resultado do envio (success, status_code, response, error)
        """
        # Formatar payload de acordo com o tipo
        if webhook.webhook_type == WebhookConfig.WebhookType.DISCORD:
            payload = WebhookService.format_discord_payload(chamado, event)
        elif webhook.webhook_type == WebhookConfig.WebhookType.SLACK:
            payload = WebhookService.format_slack_payload(chamado, event)
        else:
            payload = WebhookService.format_custom_payload(chamado, event)

        # Obter URL descriptografada
        try:
            url = webhook.get_url()
        except Exception as e:
            error_msg = f"Erro ao descriptografar URL do webhook: {e}"
            logger.error(error_msg)
            WebhookService._log_webhook(
                webhook=webhook,
                chamado=chamado,
                event=event,
                status=WebhookLog.Status.FAILED,
                payload=payload,
                error_message=error_msg
            )
            return {
                "success": False,
                "error": error_msg
            }

        # Enviar request HTTP POST
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )

            success = response.status_code in (200, 201, 202, 204)

            # Log do resultado
            WebhookService._log_webhook(
                webhook=webhook,
                chamado=chamado,
                event=event,
                status=WebhookLog.Status.SUCCESS if success else WebhookLog.Status.FAILED,
                payload=payload,
                response_status_code=response.status_code,
                response_body=response.text[:1000]  # Limitar a 1000 chars
            )

            # Atualizar estatisticas
            webhook.increment_stats(success=success)

            if success:
                logger.info(
                    f"Webhook '{webhook.name}' enviado com sucesso "
                    f"(status {response.status_code})"
                )
            else:
                logger.warning(
                    f"Webhook '{webhook.name}' falhou "
                    f"(status {response.status_code}): {response.text[:200]}"
                )

            return {
                "success": success,
                "status_code": response.status_code,
                "response": response.text[:500]
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Erro ao enviar webhook: {e}"
            logger.error(error_msg)

            WebhookService._log_webhook(
                webhook=webhook,
                chamado=chamado,
                event=event,
                status=WebhookLog.Status.FAILED,
                payload=payload,
                error_message=error_msg
            )

            webhook.increment_stats(success=False)

            return {
                "success": False,
                "error": error_msg
            }

    @staticmethod
    def _log_webhook(
        webhook: WebhookConfig,
        chamado: Chamado,
        event: str,
        status: str,
        payload: Dict[str, Any],
        response_status_code: int = None,
        response_body: str = "",
        error_message: str = "",
        retry_count: int = 0
    ):
        """
        Cria log de entrega de webhook.

        Args:
            webhook: Configuracao do webhook
            chamado: Instancia do chamado
            event: Nome do evento
            status: Status da entrega (SUCCESS, FAILED, RETRYING)
            payload: Payload enviado
            response_status_code: HTTP status code da resposta
            response_body: Corpo da resposta
            error_message: Mensagem de erro (se houver)
            retry_count: Numero de tentativas
        """
        WebhookLog.objects.create(
            webhook=webhook,
            chamado=chamado,
            event=event,
            status=status,
            payload_sent=payload,
            response_status_code=response_status_code,
            response_body=response_body,
            error_message=error_message,
            retry_count=retry_count
        )
