"""
Ponto de entrada unico da analise de IA de um atendimento. Usado por
`atendimento/tasks.py` (Celery) e por testes/comandos administrativos.
"""

import logging

logger = logging.getLogger(__name__)


def analisar_atendimento(atendimento_id: int) -> dict:
    """Roda o grafo LangGraph completo para um atendimento e retorna o estado final."""
    from .graph import build_graph

    grafo = build_graph()
    return grafo.invoke({"atendimento_id": atendimento_id, "erros": []})
