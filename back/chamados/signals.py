"""
Django Signals para auto-trigger de notificacoes e webhooks.
Permite disparar eventos sem modificar views existentes.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from chamados.models import Chamado, Notification
from chamados.services.notification_service import NotificationService
from chamados.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Chamado)
def chamado_created_handler(sender, instance, created, **kwargs):
    """
    Dispara quando um chamado e criado.
    Envia notificacoes para admins e dispara webhooks configurados.

    Args:
        sender: Model class (Chamado)
        instance: Instancia do chamado criado
        created: True se foi criado (nao atualizado)
    """
    if not created:
        return  # Ignora updates

    logger.info(f"Signal: Novo chamado criado - {instance.protocolo}")

    try:
        # Notificar admins
        NotificationService.notify_chamado_created(instance)

        # Disparar webhooks
        WebhookService.trigger_webhooks(instance, event="chamado_created")

    except Exception as e:
        logger.error(f"Erro ao processar signal de chamado criado: {e}")


@receiver(pre_save, sender=Chamado)
def chamado_pre_save_handler(sender, instance, **kwargs):
    """
    Captura o estado anterior do chamado antes de salvar.
    Necessario para detectar mudancas de prioridade e atendente.

    Args:
        sender: Model class (Chamado)
        instance: Instancia do chamado que sera salva
    """
    if instance.pk:  # Se ja existe no banco
        try:
            # Buscar estado anterior
            instance._old_instance = Chamado.objects.get(pk=instance.pk)
        except Chamado.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(post_save, sender=Chamado)
def chamado_post_save_handler(sender, instance, created, **kwargs):
    """
    Detecta mudancas de prioridade e atendente apos salvar.

    Args:
        sender: Model class (Chamado)
        instance: Instancia do chamado salvo
        created: True se foi criado
    """
    if created:
        return  # Ignora criacao (ja tratado em chamado_created_handler)

    old_instance = getattr(instance, "_old_instance", None)
    if not old_instance:
        return

    try:
        # Detectar mudanca de prioridade para URGENTE
        if (
            old_instance.prioridade != Chamado.Prioridade.URGENTE
            and instance.prioridade == Chamado.Prioridade.URGENTE
        ):
            logger.info(
                f"Signal: Prioridade mudou para URGENTE - {instance.protocolo}"
            )

            # Notificar admins e atendente
            NotificationService.notify_priority_changed(instance)

            # Disparar webhooks
            WebhookService.trigger_webhooks(instance, event="priority_urgent")

        # Detectar atribuicao de atendente
        if old_instance.atendente_id != instance.atendente_id and instance.atendente:
            logger.info(
                f"Signal: Atendente atribuido - {instance.protocolo} -> "
                f"{instance.atendente.username}"
            )

            # Notificar atendente
            NotificationService.notify_chamado_assigned(instance, instance.atendente)

            # Disparar webhooks
            WebhookService.trigger_webhooks(instance, event="chamado_assigned")

        # Detectar conclusão do chamado
        if (
            old_instance.status != Chamado.Status.RESOLVIDO
            and instance.status == Chamado.Status.RESOLVIDO
        ):
            logger.info(
                f"Signal: Chamado concluído - {instance.protocolo}"
            )

            # Enviar e-mail de conclusão via Celery
            from chamados.tasks import enviar_email_chamado_concluido_task
            enviar_email_chamado_concluido_task.delay(
                chamado_id=instance.id,
                atendente_id=instance.atendente_id if instance.atendente else None
            )

    except Exception as e:
        logger.error(f"Erro ao processar signal de chamado atualizado: {e}")
    finally:
        # Limpar instancia antiga
        if hasattr(instance, "_old_instance"):
            delattr(instance, "_old_instance")
