"""
Agente 7 - Auditoria e Explicacao.

100% Python, ZERO chamadas de LLM. Reaproveita `AuditService.checar_
consistencia` (checagens deterministicas sobre o estado final do grafo) em
vez de gerar a explicacao final via LLM -- a explicacao textual em si ja e
produzida deterministicamente por `AuditService.gerar_explicacao` a partir
da `AuditoriaClassificacao` persistida (ver `persistir_resultado_node`),
reduzindo risco de alucinacao na explicacao mostrada ao usuario.

Nunca revela chain-of-thought, prompts internos ou raciocinio privado dos
outros agentes -- `checar_consistencia` so olha para os campos estruturados
ja validados por schema de cada agente.

Campos de estado que este agente pode escrever: `agente7_resultado`, `erros`.
"""

from ...services.audit_service import AuditService


def agente7_node(state: dict) -> dict:
    resultado = AuditService.checar_consistencia(state)
    return {"agente7_resultado": resultado, "erros": []}
