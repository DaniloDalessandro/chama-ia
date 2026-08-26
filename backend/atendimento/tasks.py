"""
Celery tasks da analise de IA de atendimentos. Funciona em modo sincrono se
Celery nao estiver disponivel (mesmo padrao de `chamados/tasks.py`).

Idempotencia: cada execucao SEMPRE roda o pipeline completo e cria uma nova
AuditoriaClassificacao (append-only, decisao ja tomada na Fase 1) --
reprocessar e sempre reprocessar de verdade, pois podem existir mensagens
novas desde a ultima rodada. Nao ha lock/dedup.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    def shared_task(bind=False, max_retries=3, default_retry_delay=60):
        def decorator(func):
            def wrapper(*args, **kwargs):
                if bind and args:
                    return func(*args, **kwargs)
                return func(*args, **kwargs)
            wrapper.delay = lambda *a, **k: wrapper(*a, **k)
            wrapper.apply_async = lambda *a, **k: wrapper(*a, **k)
            return wrapper
        return decorator


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analisar_atendimento_ia_task(self, atendimento_id: int, mensagem_id: int = None):
    """
    Roda a analise de IA completa (7 agentes via LangGraph) para um atendimento.
    A indisponibilidade da DeepSeek nunca impede a criacao do atendimento --
    esta task e sempre disparada DEPOIS que o atendimento ja existe.
    """
    from .ai.orchestrator import analisar_atendimento
    from .models import Atendimento

    try:
        atendimento = Atendimento.objects.get(pk=atendimento_id)
    except Atendimento.DoesNotExist:
        logger.error("analisar_atendimento_ia_task: atendimento %s nao encontrado.", atendimento_id)
        return {"success": False, "error": "Atendimento nao encontrado"}

    atendimento.analise_ia_status = Atendimento.AnaliseIAStatus.PROCESSANDO
    atendimento.save(update_fields=["analise_ia_status"])

    try:
        resultado = analisar_atendimento(atendimento_id)
        return {"success": True, "atendimento_id": atendimento_id, "auditoria_id": resultado.get("auditoria_id")}
    except Exception as exc:  # noqa: BLE001 - qualquer falha nao tratada marca ERRO, nunca deixa PROCESSANDO travado
        logger.error("analisar_atendimento_ia_task: falha ao processar atendimento %s: %s", atendimento_id, exc)
        atendimento.analise_ia_status = Atendimento.AnaliseIAStatus.ERRO
        atendimento.save(update_fields=["analise_ia_status"])

        if CELERY_AVAILABLE and hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise
