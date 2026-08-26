"""
Estado do grafo LangGraph da analise de um atendimento.

TypedDict (nao Pydantic) por ser o padrao canonico do LangGraph -- evita
revalidar o estado inteiro a cada "hop" de no, e permite reducers
(`Annotated[..., operator.add]`) necessarios para o fan-out paralelo dos
Agentes 1 e 2. Cada agente ainda valida sua propria saida com um schema
Pydantic (ver `schemas.py`) ANTES de escrever no estado como dict simples.
"""

import operator
from typing import Annotated, Optional, TypedDict


class AtendimentoAnaliseState(TypedDict, total=False):
    atendimento_id: int
    mensagem_atual_id: Optional[int]

    texto_sanitizado: dict  # ChatSecurityService.analisar() output
    conversa_ordenada: list  # ConversationExtractionService output
    anexos_texto: list  # AttachmentExtractionService output
    anexos_imagem_ocr: list  # OCRService output, um por anexo de imagem

    agente1_resultado: Optional[dict]
    agente2_resultado: Optional[dict]
    agente3_resultado: Optional[dict]
    agente4_resultado: Optional[dict]
    agente5_resultado: Optional[dict]
    agente6_resultado: Optional[dict]
    agente7_resultado: Optional[dict]

    versao_ahp_id: Optional[int]
    auditoria_id: Optional[int]

    # Reducer: Agentes 1 e 2 rodam em paralelo e podem escrever aqui ao mesmo
    # tempo -- operator.add concatena as listas em vez de uma sobrescrever a outra.
    erros: Annotated[list, operator.add]
