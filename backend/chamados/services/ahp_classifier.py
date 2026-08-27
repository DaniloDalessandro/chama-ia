"""
Classificacao de prioridade de Chamados via AHP.

Fluxo:
  1. LLM (Groq) avalia as intensidades de URGENCIA, IMPACTO_NO_CLIENTE e
     SENTIMENTO_DO_CLIENTE a partir do texto do chamado.
  2. TEMPO_DE_ESPERA e calculado deterministicamente por faixas de tempo.
  3. O AHP matematico (VersaoAHP ativa) combina as intensidades e retorna
     a prioridade P1-P4.
  4. P1->urgente, P2->alta, P3->media, P4->baixa.

Retorna None (sem alterar prioridade) se nao houver versao AHP ativa ou
se o Groq nao estiver configurado -- nenhum erro e propagado.
"""

import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_CRITERIOS_INTERPRETATIVOS = ["URGENCIA", "IMPACTO_NO_CLIENTE", "SENTIMENTO_DO_CLIENTE"]

_PRIORIDADE_MAP = {
    "p1": "urgente",
    "p2": "alta",
    "p3": "media",
    "p4": "baixa",
}

_TEMPLATE = """Voce e um assistente especializado em suporte tecnico.
Avalie a INTENSIDADE de cada criterio abaixo com base no chamado do cliente.

CRITERIOS (use exatamente um dos codigos listados para cada):
{criterios_e_intensidades}

CHAMADO:
Assunto: {assunto}
Descricao: {descricao}

Responda APENAS com JSON valido, sem texto adicional:
{{
  "avaliacoes": [
    {{"criterio_codigo": "URGENCIA", "intensidade_codigo": "<codigo>", "justificativa": "<motivo breve>"}},
    {{"criterio_codigo": "IMPACTO_NO_CLIENTE", "intensidade_codigo": "<codigo>", "justificativa": "<motivo breve>"}},
    {{"criterio_codigo": "SENTIMENTO_DO_CLIENTE", "intensidade_codigo": "<codigo>", "justificativa": "<motivo breve>"}}
  ]
}}"""


def _criterios_e_intensidades_texto() -> str:
    from ahp.models import Criterio
    linhas = []
    for codigo in _CRITERIOS_INTERPRETATIVOS:
        try:
            criterio = Criterio.objects.get(codigo=codigo)
            codigos = list(
                criterio.intensidades.filter(ativo=True).order_by("ordem").values_list("codigo", flat=True)
            )
            linhas.append(f"- {codigo}: {codigos}")
        except Criterio.DoesNotExist:
            pass
    return "\n".join(linhas)


def _build_llm():
    """Constroi o LLM usando DeepSeek (via API compativel com OpenAI)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.DEEPSEEK_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        temperature=0.1,
        max_tokens=500,
    )


def _avaliar_intensidades_llm(chamado) -> dict:
    """
    Usa xAI (ou Groq como fallback) para avaliar URGENCIA, IMPACTO_NO_CLIENTE
    e SENTIMENTO_DO_CLIENTE. Retorna dict {criterio_codigo: intensidade_codigo}.
    """
    import json

    llm = _build_llm()

    prompt = _TEMPLATE.format(
        criterios_e_intensidades=_criterios_e_intensidades_texto(),
        assunto=chamado.assunto or "",
        descricao=(chamado.descricao or "")[:1500],
    )

    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Extrair JSON mesmo que haja texto ao redor
    start = raw.find("{")
    end = raw.rfind("}") + 1
    data = json.loads(raw[start:end])

    resultado = {}
    for avaliacao in data.get("avaliacoes", []):
        resultado[avaliacao["criterio_codigo"]] = avaliacao["intensidade_codigo"]

    return resultado


def _validar_intensidades(intensidades_brutas: dict) -> dict:
    """
    Valida cada codigo de intensidade contra o banco. Substitui invalidos
    por 'moderada' (nao forca revisao humana como no atendimento, apenas
    usa um fallback razoavel).
    """
    from ahp.models import Intensidade

    validadas = {}
    for criterio_codigo, intensidade_codigo in intensidades_brutas.items():
        existe = Intensidade.objects.filter(
            criterio__codigo=criterio_codigo,
            codigo=intensidade_codigo,
            ativo=True,
        ).exists()
        if existe:
            validadas[criterio_codigo] = intensidade_codigo
        else:
            logger.warning(
                f"AHP Chamado: intensidade '{intensidade_codigo}' invalida para "
                f"criterio '{criterio_codigo}', usando 'moderada'."
            )
            validadas[criterio_codigo] = "moderada"
    return validadas


def _get_tempo_espera_intensidade(chamado) -> str:
    """Calcula TEMPO_DE_ESPERA deterministicamente pelas faixas cadastradas."""
    from ahp.models import FaixaTempoEspera, CODIGO_TEMPO_DE_ESPERA, Criterio

    try:
        minutos = max(0.0, (timezone.now() - chamado.created_at).total_seconds() / 60.0)
        criterio = Criterio.objects.get(codigo=CODIGO_TEMPO_DE_ESPERA)
        for faixa in criterio.faixas_tempo.filter(ativo=True).order_by("minutos_min"):
            if minutos < faixa.minutos_min:
                continue
            if faixa.minutos_max is None or minutos < faixa.minutos_max:
                return faixa.intensidade.codigo
    except Exception as exc:
        logger.warning(f"AHP Chamado: erro ao calcular TEMPO_DE_ESPERA: {exc}")
    return "baixa"


def classificar_prioridade_ahp(chamado) -> dict | None:
    """
    Classifica a prioridade do chamado usando AHP.

    Retorna:
        {
            "prioridade": "urgente"|"alta"|"media"|"baixa",
            "prioridade_ahp": "p1"|"p2"|"p3"|"p4",
            "indice": float,
            "intensidades": {criterio: intensidade},
            "versao_ahp_id": int,
        }
        ou None se AHP nao estiver disponivel.
    """
    # Verificar versao AHP ativa
    try:
        from ahp.models import VersaoAHP
        from ahp.services.version_service import AHPVersionService

        versao = VersaoAHP.objects.filter(estado=VersaoAHP.Estado.ATIVA).first()
        if not versao:
            logger.info("AHP Chamado: nenhuma versao AHP ativa. Pulando classificacao AHP.")
            return None
    except Exception as exc:
        logger.warning(f"AHP Chamado: erro ao buscar versao AHP: {exc}")
        return None

    # Verificar DeepSeek disponivel
    if not getattr(settings, "DEEPSEEK_API_KEY", None):
        logger.info("AHP Chamado: DEEPSEEK_API_KEY nao configurado. Pulando classificacao AHP.")
        return None

    try:
        # 1. LLM avalia intensidades interpretativas
        intensidades_brutas = _avaliar_intensidades_llm(chamado)
        intensidades = _validar_intensidades(intensidades_brutas)

        # 2. TEMPO_DE_ESPERA deterministico
        intensidades["TEMPO_DE_ESPERA"] = _get_tempo_espera_intensidade(chamado)

        logger.info(f"AHP Chamado #{chamado.protocolo}: intensidades={intensidades}")

        # 3. Calcular prioridade via AHP
        from atendimento.services.classification_service import ServicePriorityClassificationService

        resultado = ServicePriorityClassificationService.classify_from_intensidades(
            versao, intensidades
        )

        prioridade_ahp = (resultado.prioridade or "p4").lower()
        prioridade = _PRIORIDADE_MAP.get(prioridade_ahp, "media")
        indice = resultado.indice or 0.0

        logger.info(
            f"AHP Chamado #{chamado.protocolo}: indice={indice:.2f} "
            f"-> {prioridade_ahp} -> {prioridade}"
        )

        return {
            "prioridade": prioridade,
            "prioridade_ahp": prioridade_ahp,
            "indice": indice,
            "intensidades": intensidades,
            "versao_ahp_id": versao.id,
        }

    except Exception as exc:
        logger.error(f"AHP Chamado #{chamado.protocolo}: erro na classificacao AHP: {exc}", exc_info=True)
        return None
