"""
Factory do cliente DeepSeek: usa langchain_openai.ChatOpenAI apontado para o
base_url da DeepSeek (API compativel com OpenAI Chat Completions). Timeout e
retry com backoff sao delegados nativamente ao ChatOpenAI/SDK OpenAI -- nenhum
loop de retry customizado e necessario.

Segue o mesmo idioma de degradacao graciosa de `chamados.services.ia_classifier
.IAClassifierService`: sem DEEPSEEK_API_KEY configurada, retorna None e quem
chamou decide o fallback deterministico -- nunca levanta excecao aqui.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def build_deepseek_llm(*, temperature: float = 0.1, max_tokens: int = 800):
    """Retorna um ChatOpenAI apontado para a DeepSeek, ou None em modo degradado."""
    if not settings.DEEPSEEK_API_KEY:
        return None

    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.DEEPSEEK_TIMEOUT,
            max_retries=settings.DEEPSEEK_MAX_RETRIES,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 - nunca derruba o agente por falha de construcao do cliente
        logger.error("Erro ao inicializar ChatOpenAI (DeepSeek, modelo=%s): %s", settings.DEEPSEEK_MODEL, exc)
        return None


def build_chain(llm, prompt, output_schema):
    """chain = prompt | llm | JsonOutputParser(pydantic_object=output_schema), ou None se llm for None."""
    if llm is None:
        return None

    try:
        from langchain_core.output_parsers import JsonOutputParser

        parser = JsonOutputParser(pydantic_object=output_schema)
        return prompt | llm | parser
    except Exception as exc:  # noqa: BLE001
        logger.error("Erro ao montar chain para %s: %s", output_schema.__name__, exc)
        return None


def invoke_chain_or_fallback(chain, variables: dict, output_schema, fallback, agente_nome: str) -> tuple:
    """
    Invoca `chain` e valida a saida contra `output_schema`. Em qualquer falha
    (chain None, timeout, erro de rede, JSON invalido, schema invalido) NUNCA
    levanta excecao -- retorna `fallback` (uma instancia ja construida de
    `output_schema`, representando o estado seguro/degradado daquele agente).

    Retorna (resultado_dict, erros: list[dict]).
    """
    if chain is not None:
        try:
            bruto = chain.invoke(variables)
            validado = output_schema(**bruto)
            return validado.model_dump(), []
        except Exception as exc:  # noqa: BLE001 - qualquer falha vira fallback, nunca propaga
            logger.error("Agente %s: falha ao invocar/validar chain (%s)", agente_nome, exc)
            return fallback.model_dump(), [
                {"agente": agente_nome, "erro": f"Falha na chamada a DeepSeek: {exc}"}
            ]

    return fallback.model_dump(), [
        {"agente": agente_nome, "erro": "DeepSeek indisponivel (sem API key configurada); usando fallback deterministico."}
    ]
