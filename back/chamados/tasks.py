"""
Celery tasks para processamento assincrono de chamados com IA.
Funciona em modo sincrono se Celery nao estiver disponivel.
"""

import logging

logger = logging.getLogger(__name__)

# Tentar importar Celery, se nao conseguir, criar decorador fake
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Decorador fake que apenas executa a funcao normalmente
    def shared_task(bind=False, max_retries=3, default_retry_delay=60):
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Remove 'self' se bind=True foi usado
                if bind and args:
                    return func(*args, **kwargs)
                return func(*args, **kwargs)
            wrapper.delay = lambda *args, **kwargs: wrapper(*args, **kwargs)
            wrapper.apply_async = lambda *args, **kwargs: wrapper(*args, **kwargs)
            return wrapper
        return decorator


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def processar_chamado_ia_task(self, chamado_id: int):
    """
    Task para processar um chamado com IA.

    Fluxo:
    1. Classificar chamado com Gemini
    2. Gerar embedding do texto
    3. Buscar chamados similares resolvidos
    4. Atualizar chamado com resultados
    5. Auto-aplicar prioridade se financeiro/urgente
    6. Registrar no historico

    Args:
        chamado_id: ID do chamado a processar

    Returns:
        Dicionario com resultado do processamento
    """
    from chamados.services.ia_classifier import processar_chamado_completo

    try:
        logger.info(f"Iniciando processamento IA do chamado {chamado_id}")

        resultado = processar_chamado_completo(chamado_id)

        if resultado["success"]:
            logger.info(
                f"Chamado {chamado_id} processado com sucesso. "
                f"Categoria: {resultado['classificacao']['categoria']}, "
                f"Prioridade: {resultado['classificacao']['prioridade_sugerida']}, "
                f"Recorrente: {resultado['similaridade']['is_recorrente']}"
            )
        else:
            logger.warning(f"Falha ao processar chamado {chamado_id}: {resultado.get('error')}")

        return resultado

    except Exception as exc:
        logger.error(f"Erro ao processar chamado {chamado_id}: {exc}")
        # Se Celery estiver disponivel e tiver retry
        if CELERY_AVAILABLE and hasattr(self, 'retry'):
            raise self.retry(exc=exc)
        raise


@shared_task(bind=False)
def reprocessar_chamados_pendentes():
    """
    Task para reprocessar chamados que ainda nao foram processados pela IA.
    Pode ser agendada periodicamente via Celery Beat.
    """
    from chamados.models import Chamado

    chamados_pendentes = Chamado.objects.filter(
        ia_processed=False,
        status__in=["aberto", "em_analise", "em_atendimento"]
    ).values_list("id", flat=True)[:100]  # Limitar a 100 por vez

    logger.info(f"Reprocessando {len(chamados_pendentes)} chamados pendentes")

    for chamado_id in chamados_pendentes:
        processar_chamado_ia_task.delay(chamado_id)

    return {"total_enfileirados": len(chamados_pendentes)}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_email_confirmacao_task(self, chamado_id: int):
    """
    Task para enviar e-mail de confirmacao de abertura de chamado.
    """
    from chamados.models import Chamado
    from chamados.services.email_service import enviar_email_confirmacao_chamado

    try:
        chamado = Chamado.objects.get(id=chamado_id)
        resultado = enviar_email_confirmacao_chamado(chamado)
        if resultado:
            logger.info(f"E-mail de confirmacao enviado via Celery para chamado {chamado_id}")
        else:
            logger.warning(f"Falha ao enviar e-mail de confirmacao para chamado {chamado_id}")
        return {"success": resultado, "chamado_id": chamado_id}
    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} nao encontrado para envio de e-mail")
        return {"success": False, "error": "Chamado nao encontrado"}
    except Exception as exc:
        logger.error(f"Erro ao enviar e-mail para chamado {chamado_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def processar_chamado_ia_async_task(self, chamado_id: int):
    """
    Task assincrona para processar chamado com IA (fluxo completo).
    Equivalente ao que ChamadoPublicoProcessarIAView.post() faz sincronamente:
    classificar + mudar status.
    """
    from chamados.models import Chamado
    from chamados.services.ia_classifier import processar_chamado_completo

    try:
        chamado = Chamado.objects.get(id=chamado_id)

        if chamado.ia_processed:
            logger.info(f"Chamado {chamado_id} ja processado, ignorando")
            return {"success": True, "chamado_id": chamado_id, "already_processed": True}

        logger.info(f"Iniciando processamento IA async do chamado {chamado_id}")
        resultado = processar_chamado_completo(chamado_id)

        if resultado["success"]:
            chamado.refresh_from_db()
            if not chamado.is_recorrente:
                chamado.status = Chamado.Status.EM_ANALISE
                chamado.save()
            logger.info(
                f"Chamado {chamado_id} processado async com sucesso. "
                f"Categoria: {resultado['classificacao']['categoria']}"
            )
        else:
            logger.warning(f"Falha no processamento async do chamado {chamado_id}: {resultado.get('error')}")

        return resultado

    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} nao encontrado para processamento IA async")
        return {"success": False, "error": "Chamado nao encontrado"}
    except Exception as exc:
        logger.error(f"Erro no processamento IA async do chamado {chamado_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise


def processar_chamado_sync(chamado_id: int) -> dict:
    """
    Processa chamado de forma sincrona (sem Celery).
    Use esta funcao quando quiser garantir processamento imediato.
    """
    from chamados.services.ia_classifier import processar_chamado_completo
    return processar_chamado_completo(chamado_id)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_email_atualizacao_status_task(self, chamado_id: int, status_anterior: str, usuario_id: int = None):
    """
    Task para enviar email de atualização de status.
    """
    from chamados.models import Chamado
    from chamados.services.email_service import enviar_email_atualizacao_status
    from django.contrib.auth import get_user_model

    try:
        chamado = Chamado.objects.get(id=chamado_id)
        usuario = None
        if usuario_id:
            User = get_user_model()
            try:
                usuario = User.objects.get(id=usuario_id)
            except User.DoesNotExist:
                pass

        resultado = enviar_email_atualizacao_status(chamado, status_anterior, usuario)
        if resultado:
            logger.info(f"Email de atualização de status enviado para chamado {chamado_id}")
        else:
            logger.warning(f"Falha ao enviar email de atualização para chamado {chamado_id}")
        return {"success": resultado, "chamado_id": chamado_id}
    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} não encontrado para envio de email")
        return {"success": False, "error": "Chamado não encontrado"}
    except Exception as exc:
        logger.error(f"Erro ao enviar email de atualização para chamado {chamado_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_email_atribuicao_task(self, chamado_id: int, atendente_id: int):
    """
    Task para enviar email de atribuição para atendente.
    """
    from chamados.models import Chamado
    from chamados.services.email_service import enviar_email_atribuicao
    from django.contrib.auth import get_user_model

    try:
        chamado = Chamado.objects.get(id=chamado_id)
        User = get_user_model()
        atendente = User.objects.get(id=atendente_id)

        resultado = enviar_email_atribuicao(chamado, atendente)
        if resultado:
            logger.info(f"Email de atribuição enviado para {atendente.email} - Chamado {chamado_id}")
        else:
            logger.warning(f"Falha ao enviar email de atribuição para chamado {chamado_id}")
        return {"success": resultado, "chamado_id": chamado_id}
    except (Chamado.DoesNotExist, User.DoesNotExist) as e:
        logger.error(f"Erro: {e}")
        return {"success": False, "error": str(e)}
    except Exception as exc:
        logger.error(f"Erro ao enviar email de atribuição para chamado {chamado_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_email_novo_comentario_task(self, comentario_id: str):
    """
    Task para enviar email de novo comentário.
    """
    from chamados.models import ComentarioChamado
    from chamados.services.email_service import enviar_email_novo_comentario

    try:
        comentario = ComentarioChamado.objects.select_related('chamado').get(id=comentario_id)
        chamado = comentario.chamado

        resultado = enviar_email_novo_comentario(chamado, comentario)
        if resultado:
            logger.info(f"Email de comentário enviado para chamado {chamado.id}")
        else:
            logger.warning(f"Falha ao enviar email de comentário para chamado {chamado.id}")
        return {"success": resultado, "comentario_id": str(comentario_id)}
    except ComentarioChamado.DoesNotExist:
        logger.error(f"Comentário {comentario_id} não encontrado para envio de email")
        return {"success": False, "error": "Comentário não encontrado"}
    except Exception as exc:
        logger.error(f"Erro ao enviar email de comentário {comentario_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_webhook_task(self, webhook_id: str, chamado_id: int, event: str):
    """
    Task para enviar webhook HTTP com retry automatico.

    Args:
        webhook_id: ID da configuracao do webhook
        chamado_id: ID do chamado
        event: Nome do evento (chamado_created, chamado_assigned, priority_urgent)

    Returns:
        Dict com resultado do envio
    """
    from chamados.models import WebhookConfig, Chamado, WebhookLog
    from chamados.services.webhook_service import WebhookService

    try:
        webhook = WebhookConfig.objects.get(id=webhook_id)
        chamado = Chamado.objects.get(id=chamado_id)

        logger.info(
            f"Enviando webhook '{webhook.name}' para evento '{event}' "
            f"do chamado {chamado.protocolo}"
        )

        # Enviar webhook
        resultado = WebhookService.send_webhook(webhook, chamado, event)

        # Se falhou e ainda tem retries, tentar novamente
        if not resultado.get("success") and CELERY_AVAILABLE and hasattr(self, "retry"):
            logger.warning(
                f"Webhook '{webhook.name}' falhou. Tentando novamente em 60s..."
            )
            raise self.retry(
                exc=Exception(resultado.get("error", "Webhook failed")),
                countdown=60  # Esperar 60 segundos antes de tentar novamente
            )

        return resultado

    except WebhookConfig.DoesNotExist:
        logger.error(f"WebhookConfig {webhook_id} nao encontrado")
        return {"success": False, "error": "Webhook nao encontrado"}
    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} nao encontrado")
        return {"success": False, "error": "Chamado nao encontrado"}
    except Exception as exc:
        logger.error(f"Erro ao enviar webhook {webhook_id}: {exc}")
        # Se for a ultima tentativa, logar como falha final
        if CELERY_AVAILABLE and hasattr(self, "request"):
            if self.request.retries >= self.max_retries:
                logger.error(f"Webhook {webhook_id} falhou apos {self.max_retries} tentativas")
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def enviar_email_chamado_concluido_task(self, chamado_id: int, atendente_id: int = None):
    """
    Task para enviar email de chamado concluído.

    Args:
        chamado_id: ID do chamado
        atendente_id: ID do atendente que concluiu (opcional)

    Returns:
        Dict com resultado do envio
    """
    from chamados.models import Chamado
    from chamados.services.email_service import enviar_email_chamado_concluido
    from django.contrib.auth import get_user_model

    try:
        chamado = Chamado.objects.get(id=chamado_id)
        atendente = None

        if atendente_id:
            User = get_user_model()
            try:
                atendente = User.objects.get(id=atendente_id)
            except User.DoesNotExist:
                pass

        resultado = enviar_email_chamado_concluido(chamado, atendente)

        if resultado:
            logger.info(f"Email de conclusão enviado para {chamado.email} - Chamado {chamado.id}")
        else:
            logger.warning(f"Falha ao enviar email de conclusão para chamado {chamado.id}")

        return {"success": resultado, "chamado_id": chamado_id}

    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} não encontrado para envio de email de conclusão")
        return {"success": False, "error": "Chamado não encontrado"}
    except Exception as exc:
        logger.error(f"Erro ao enviar email de conclusão para chamado {chamado_id}: {exc}")
        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise
