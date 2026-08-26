"""
Grafo LangGraph da analise de um atendimento:

START -> validacao_seguranca -> [agente1, agente2] (paralelo) -> agente3 (fan-in)
      -> agente4 -> agente5 -> agente6 -> agente7 -> persistir_resultado -> END

Grafo linear fixo, sem arestas condicionais nem abortos: cada no sempre
produz uma saida valida (possivelmente degradada), garantindo que nenhuma
mensagem seja perdida e que o atendimento sempre chegue a persistir_resultado
(mesmo que Agente 6 falhe -- nesse caso, sem AuditoriaClassificacao nova,
apenas analise_ia_status=ERRO).

# TODO(Fase 3): apos persistir_resultado, disparar reordenacao da fila aqui.
"""

import logging

from langgraph.graph import END, START, StateGraph

from .agents.agente1_conversa import agente1_node
from .agents.agente2_visual_ocr import agente2_node
from .agents.agente3_termos_contexto import agente3_node
from .agents.agente4_avaliacao_criterios import agente4_node
from .agents.agente5_validacao_critica import agente5_node
from .agents.agente6_ahp import agente6_node
from .agents.agente7_auditoria import agente7_node
from .state import AtendimentoAnaliseState

logger = logging.getLogger(__name__)


def validacao_seguranca_node(state: dict) -> dict:
    """
    Primeiro no do grafo: prepara TODO o material determinístico (zero LLM)
    que os agentes 1 e 2 vao consumir -- ChatSecurityService (informativo),
    ConversationExtractionService, AttachmentExtractionService e OCRService.
    """
    from ..models import Atendimento, AnexoAtendimento
    from ..services.attachment_extraction_service import AttachmentExtractionService
    from ..services.chat_security_service import ChatSecurityService
    from ..services.conversation_extraction_service import ConversationExtractionService
    from ..services.ocr_service import OCRService

    atendimento_id = state["atendimento_id"]
    try:
        atendimento = Atendimento.objects.get(pk=atendimento_id)
    except Atendimento.DoesNotExist:
        logger.error("validacao_seguranca: atendimento %s nao encontrado.", atendimento_id)
        return {"erros": [{"agente": "validacao_seguranca", "erro": f"Atendimento {atendimento_id} nao encontrado."}]}

    texto_sanitizado = ChatSecurityService.analisar(atendimento)
    conversa_ordenada = ConversationExtractionService.get_historico_ordenado(atendimento)
    anexos_texto = AttachmentExtractionService.extract_all(atendimento)

    anexos_imagem_ocr = []
    for anexo in atendimento.anexos.filter(tipo_arquivo=AnexoAtendimento.TipoArquivo.IMAGEM):
        anexo.arquivo.open("rb")
        try:
            conteudo = anexo.arquivo.read()
        finally:
            anexo.arquivo.close()
        resultado_ocr = OCRService.extract_text(conteudo)
        anexos_imagem_ocr.append({"anexo_id": str(anexo.id), **resultado_ocr})

    return {
        "texto_sanitizado": texto_sanitizado,
        "conversa_ordenada": conversa_ordenada,
        "anexos_texto": anexos_texto,
        "anexos_imagem_ocr": anexos_imagem_ocr,
        "erros": [],
    }


def _persistir_regra_critica(atendimento, agente5_resultado: dict) -> None:
    from ahp.models import Criterio, Termo

    from ..models import RegraCriticaAtendimento

    criterio_gatilho = None
    if agente5_resultado.get("criterio_gatilho_codigo"):
        criterio_gatilho = Criterio.objects.filter(codigo=agente5_resultado["criterio_gatilho_codigo"]).first()

    termo_gatilho = None
    if agente5_resultado.get("termo_gatilho_id"):
        termo_gatilho = Termo.objects.filter(id=agente5_resultado["termo_gatilho_id"]).first()

    RegraCriticaAtendimento.objects.update_or_create(
        atendimento=atendimento,
        defaults={
            "criterio_gatilho": criterio_gatilho,
            "termo_gatilho": termo_gatilho,
            "confirmada": True,
            "justificativa": agente5_resultado.get("justificativa", ""),
            "origem": RegraCriticaAtendimento.Origem.AGENTE_VALIDACAO_CRITICA,
        },
    )
    atendimento.regra_critica_confirmada = True
    atendimento.save(update_fields=["regra_critica_confirmada"])


def _popular_resumo_atendimento(atendimento, state: dict) -> None:
    """
    Preenche `resumo`/`servico_afetado`/`assunto` (secao 27, card do atendimento)
    a partir da sintese do Agente 1 -- roda mesmo se o Agente 6 tiver falhado,
    pois o Agente 1 ja rodou independentemente disso. No caminho degradado (sem
    DeepSeek), o proprio texto de fallback vira o resumo (honesto sobre o estado
    degradado, nunca escondido).
    """
    agente1 = state.get("agente1_resultado") or {}
    if not agente1:
        return

    problema = (agente1.get("problema_identificado") or "").strip()
    atendimento.resumo = problema[:2000]
    atendimento.servico_afetado = (agente1.get("servico_afetado") or "")[:255]
    atendimento.assunto = problema[:80] if problema else (atendimento.assunto or f"Atendimento #{atendimento.id}")
    atendimento.save(update_fields=["resumo", "servico_afetado", "assunto"])


def persistir_resultado_node(state: dict) -> dict:
    """
    Ultimo no do grafo. Se o Agente 6 falhou (sem VersaoAHP ativa), nao cria
    AuditoriaClassificacao (nada significativo para persistir), marca
    analise_ia_status=ERRO e NUNCA mexe em status_atendimento.
    """
    from ahp.models import VersaoAHP

    from ..models import Atendimento
    from ..services.classification_service import ResultadoClassificacao
    from ..services.persistence_service import ServicePersistenceService

    atendimento_id = state["atendimento_id"]
    agente6 = state.get("agente6_resultado")
    versao_ahp_id = state.get("versao_ahp_id")

    try:
        atendimento = Atendimento.objects.get(pk=atendimento_id)
    except Atendimento.DoesNotExist:
        logger.error("persistir_resultado: atendimento %s nao encontrado.", atendimento_id)
        return {"auditoria_id": None}

    _popular_resumo_atendimento(atendimento, state)

    if agente6 is None or versao_ahp_id is None:
        atendimento.analise_ia_status = Atendimento.AnaliseIAStatus.ERRO
        atendimento.save(update_fields=["analise_ia_status"])
        return {"auditoria_id": None}

    versao_ahp = VersaoAHP.objects.get(pk=versao_ahp_id)
    resultado = ResultadoClassificacao(**agente6)

    auditoria = ServicePersistenceService.persist(atendimento, resultado, versao_ahp, user=None)

    agente7 = state.get("agente7_resultado") or {}
    if agente7:
        auditoria.auditoria_ia = agente7
        auditoria.save(update_fields=["auditoria_ia"])

    agente5 = state.get("agente5_resultado") or {}
    if agente5.get("regra_critica_confirmada"):
        _persistir_regra_critica(atendimento, agente5)

    return {"auditoria_id": auditoria.id}


def build_graph():
    grafo = StateGraph(AtendimentoAnaliseState)

    grafo.add_node("validacao_seguranca", validacao_seguranca_node)
    grafo.add_node("agente1", agente1_node)
    grafo.add_node("agente2", agente2_node)
    grafo.add_node("agente3", agente3_node)
    grafo.add_node("agente4", agente4_node)
    grafo.add_node("agente5", agente5_node)
    grafo.add_node("agente6", agente6_node)
    grafo.add_node("agente7", agente7_node)
    grafo.add_node("persistir_resultado", persistir_resultado_node)

    grafo.add_edge(START, "validacao_seguranca")
    grafo.add_edge("validacao_seguranca", "agente1")
    grafo.add_edge("validacao_seguranca", "agente2")
    grafo.add_edge("agente1", "agente3")
    grafo.add_edge("agente2", "agente3")
    grafo.add_edge("agente3", "agente4")
    grafo.add_edge("agente4", "agente5")
    grafo.add_edge("agente5", "agente6")
    grafo.add_edge("agente6", "agente7")
    grafo.add_edge("agente7", "persistir_resultado")
    grafo.add_edge("persistir_resultado", END)

    return grafo.compile()
