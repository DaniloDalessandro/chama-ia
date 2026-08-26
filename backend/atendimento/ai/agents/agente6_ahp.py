"""
Agente 6 - Especialista AHP.

100% Python, ZERO chamadas de LLM -- o spec proibe explicitamente pedir a
DeepSeek para calcular autovetor/autovalor/CI/CR/pesos/normalizacao/
resultado final. Este agente apenas orquestra os servicos ja construidos na
Fase 1: carrega a VersaoAHP ativa, consolida as intensidades escolhidas
(3 do Agente 4 + TEMPO_DE_ESPERA de WaitingTimeService, deterministico) e
chama `ServicePriorityClassificationService.classify_from_intensidades`.

Campos de estado que este agente pode escrever: `agente6_resultado`,
`versao_ahp_id`, `erros`.
"""

import dataclasses
import logging

logger = logging.getLogger(__name__)

_AGENTE_NOME = "agente6_ahp"


def agente6_node(state: dict) -> dict:
    from ahp.services.version_service import AHPVersionService

    from ...models import Atendimento
    from ...services.classification_service import ServicePriorityClassificationService
    from ...services.waiting_time_service import WaitingTimeService

    atendimento_id = state.get("atendimento_id")
    try:
        atendimento = Atendimento.objects.get(pk=atendimento_id)
    except Atendimento.DoesNotExist:
        logger.error("Agente 6: atendimento %s nao encontrado.", atendimento_id)
        return {"agente6_resultado": None, "erros": [{"agente": _AGENTE_NOME, "erro": f"Atendimento {atendimento_id} nao encontrado."}]}

    versao_ahp = AHPVersionService.get_versao_ativa()
    if versao_ahp is None:
        logger.error("Agente 6: nenhuma VersaoAHP ativa.")
        return {"agente6_resultado": None, "erros": [{"agente": _AGENTE_NOME, "erro": "Nenhuma VersaoAHP ativa no momento."}]}

    agente4 = state.get("agente4_resultado") or {}
    intensidades = {
        avaliacao["criterio_codigo"]: avaliacao["intensidade_codigo"]
        for avaliacao in agente4.get("avaliacoes", [])
    }

    try:
        intensidades["TEMPO_DE_ESPERA"] = WaitingTimeService.get_intensidade_atual(atendimento).codigo
    except ValueError as exc:
        logger.error("Agente 6: falha ao calcular tempo de espera: %s", exc)
        return {
            "agente6_resultado": None, "versao_ahp_id": versao_ahp.id,
            "erros": [{"agente": _AGENTE_NOME, "erro": str(exc)}],
        }

    resultado = ServicePriorityClassificationService.classify_from_intensidades(versao_ahp, intensidades)

    return {
        "agente6_resultado": dataclasses.asdict(resultado),
        "versao_ahp_id": versao_ahp.id,
        "erros": [],
    }
