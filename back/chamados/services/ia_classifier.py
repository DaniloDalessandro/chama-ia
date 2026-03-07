"""
Servico de classificacao de chamados usando IA com LangChain + xAI Grok.
Classificacao via Grok (grok-3-mini). Similaridade via Google Embeddings (opcional).
"""

import json
import hashlib
import logging
from typing import Optional
from dataclasses import dataclass

import numpy as np
from django.conf import settings
from django.utils import timezone

from langchain_xai import ChatXAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


@dataclass
class ClassificacaoResult:
    """Resultado da classificacao IA."""
    categoria: str
    prioridade_sugerida: str
    resumo: str
    problema_principal: str
    palavras_chave: list[str]
    confianca: float
    is_financeiro_urgente: bool = False


@dataclass
class SimilaridadeResult:
    """Resultado da busca por chamados similares."""
    chamado_similar_id: Optional[int]
    similaridade_score: float
    is_recorrente: bool


# Categorias disponiveis
CATEGORIAS = {
    "financeiro": "Financeiro / Pagamento",
    "nota_fiscal": "Nota Fiscal / Boletos",
    "problema_tecnico": "Problema Tecnico",
    "login_acesso": "Login / Acesso",
    "cadastro_dados": "Cadastro / Dados",
    "atendimento": "Atendimento / Suporte",
    "solicitacao_servico": "Solicitacao de Servico",
    "reclamacao": "Reclamacao Geral",
    "outros": "Outros",
}

# Keywords que acionam prioridade URGENTE para chamados financeiros
KEYWORDS_FINANCEIRO_URGENTE = [
    "pagamento", "boleto", "cobranca", "nota fiscal", "fatura",
    "vencimento", "atraso", "multa", "juros", "estorno", "reembolso",
    "inadimplencia", "valores incorretos", "bloqueio por falta de pagamento",
    "nao consegui pagar", "vencido", "venceu", "parcela", "debito",
    "credito", "valor errado", "duplicidade", "cobranca indevida",
]


# ============================================
# Pydantic Model para Output Parsing
# ============================================

class ClassificacaoOutput(BaseModel):
    """Schema para output estruturado da classificacao."""
    categoria: str = Field(description="Codigo da categoria do chamado")
    prioridade_sugerida: str = Field(description="Nivel de prioridade: urgente, alta, media ou baixa")
    resumo: str = Field(description="Resumo do problema em 1-2 frases")
    problema_principal: str = Field(description="Identificacao do problema central")
    palavras_chave: list[str] = Field(description="Lista de 3-5 palavras-chave relevantes")
    confianca: float = Field(description="Nivel de confianca da classificacao (0.0 a 1.0)")
    is_financeiro: bool = Field(description="Se o chamado envolve aspectos financeiros")


class IAClassifierService:
    """
    Servico para classificar chamados usando LangChain + xAI Grok.
    """

    def __init__(self):
        self.llm = None
        self.chain = None

        if settings.XAI_API_KEY:
            try:
                self.llm = ChatXAI(
                    model=settings.XAI_MODEL,
                    xai_api_key=settings.XAI_API_KEY,
                    temperature=0.3,
                    max_tokens=500,
                )

                parser = JsonOutputParser(pydantic_object=ClassificacaoOutput)

                categorias_str = "\n".join([f"- {k}: {v}" for k, v in CATEGORIAS.items()])

                prompt = PromptTemplate(
                    template="""Voce e um assistente especializado em classificar chamados de suporte.

Analise o chamado abaixo e forneca uma classificacao estruturada.

REGRA CRITICA: Se o chamado mencionar QUALQUER aspecto financeiro (pagamento, boleto, cobranca, nota fiscal, fatura, vencimento, atraso, multa, juros, estorno, reembolso, valores), a prioridade DEVE ser "urgente" e is_financeiro DEVE ser true.

CATEGORIAS DISPONIVEIS:
{categorias}

PRIORIDADES DISPONIVEIS:
- urgente: Prejuizo financeiro ou risco de pagamento
- alta: Falhas que impedem funcionamento
- media: Problemas comuns, duvidas
- baixa: Sugestoes, melhorias

CHAMADO:
Assunto: {assunto}
Descricao: {descricao}

{format_instructions}

Responda APENAS com o JSON no formato especificado acima.""",
                    input_variables=["assunto", "descricao"],
                    partial_variables={
                        "format_instructions": parser.get_format_instructions(),
                        "categorias": categorias_str
                    },
                )

                self.chain = prompt | self.llm | parser

                logger.info(f"LangChain inicializado com sucesso (xAI Grok - {settings.XAI_MODEL})")

            except Exception as e:
                logger.error(f"Erro ao inicializar LangChain com Grok: {e}")

    def _check_keywords_financeiro(self, texto: str) -> bool:
        """Verifica se o texto contem keywords financeiras."""
        texto_lower = texto.lower()
        return any(keyword in texto_lower for keyword in KEYWORDS_FINANCEIRO_URGENTE)

    def classificar(self, assunto: str, descricao: str) -> ClassificacaoResult:
        """
        Classifica um chamado usando LangChain + xAI Grok.

        Args:
            assunto: Assunto do chamado
            descricao: Descricao completa do chamado

        Returns:
            ClassificacaoResult com a classificacao
        """
        if not self.chain:
            logger.warning("LangChain (Grok) nao configurado. Usando classificacao padrao.")
            return self._classificacao_padrao(assunto, descricao)

        try:
            result = self.chain.invoke({
                "assunto": assunto,
                "descricao": descricao
            })

            texto_completo = f"{assunto} {descricao}"
            is_financeiro = result.get("is_financeiro", False) or self._check_keywords_financeiro(texto_completo)

            prioridade = result.get("prioridade_sugerida", "media")
            if is_financeiro or result.get("categoria") == "financeiro":
                prioridade = "urgente"

            return ClassificacaoResult(
                categoria=result.get("categoria", "outros"),
                prioridade_sugerida=prioridade,
                resumo=result.get("resumo", ""),
                problema_principal=result.get("problema_principal", ""),
                palavras_chave=result.get("palavras_chave", [])[:10],
                confianca=min(max(result.get("confianca", 0.8), 0.0), 1.0),
                is_financeiro_urgente=is_financeiro,
            )

        except Exception as e:
            logger.error(f"Erro ao classificar com Grok: {e}")
            return self._classificacao_padrao(assunto, descricao)

    def _classificacao_padrao(self, assunto: str, descricao: str) -> ClassificacaoResult:
        """Classificacao padrao quando a IA nao esta disponivel."""
        texto = f"{assunto} {descricao}".lower()
        is_financeiro = self._check_keywords_financeiro(texto)

        categoria = "outros"
        if any(kw in texto for kw in ["nota fiscal", "nf-e", "nfe", "boleto"]):
            categoria = "nota_fiscal"
        elif any(kw in texto for kw in ["pagamento", "pagar", "financeiro", "cobranca"]):
            categoria = "financeiro"
        elif any(kw in texto for kw in ["erro", "bug", "nao funciona", "problema"]):
            categoria = "problema_tecnico"
        elif any(kw in texto for kw in ["login", "senha", "acesso", "entrar"]):
            categoria = "login_acesso"
        elif any(kw in texto for kw in ["cadastro", "dados", "atualizar"]):
            categoria = "cadastro_dados"

        prioridade = "urgente" if is_financeiro else "media"

        return ClassificacaoResult(
            categoria=categoria,
            prioridade_sugerida=prioridade,
            resumo=assunto[:200],
            problema_principal="Classificacao automatica (IA indisponivel)",
            palavras_chave=[],
            confianca=0.5,
            is_financeiro_urgente=is_financeiro,
        )


class SimilarityService:
    """
    Servico para detectar chamados recorrentes usando LangChain Embeddings (Google).
    Funciona apenas se GEMINI_API_KEY estiver configurado.
    """

    def __init__(self):
        self.embeddings = None
        self.model = settings.IA_EMBEDDING_MODEL
        self.threshold = settings.IA_SIMILARITY_THRESHOLD

        if settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model=self.model,
                    google_api_key=settings.GEMINI_API_KEY,
                    task_type="retrieval_document"
                )
                logger.info("LangChain Embeddings inicializado (Google Gemini)")
            except Exception as e:
                logger.error(f"Erro ao inicializar embeddings: {e}")
        else:
            logger.info("GEMINI_API_KEY nao configurado - deteccao de similaridade desativada")

    def _calcular_hash(self, texto: str) -> str:
        texto_normalizado = texto.strip().lower()
        return hashlib.sha256(texto_normalizado.encode('utf-8')).hexdigest()

    def _buscar_cache(self, texto_hash: str) -> Optional[list[float]]:
        from chamados.models import EmbeddingCache
        try:
            cache = EmbeddingCache.objects.filter(
                texto_hash=texto_hash,
                modelo=self.model
            ).first()
            if cache:
                cache.uso_count += 1
                cache.save(update_fields=['uso_count', 'last_used_at'])
                return cache.embedding_vector
            return None
        except Exception as e:
            logger.warning(f"Erro ao buscar cache: {e}")
            return None

    def _salvar_cache(self, texto_hash: str, embedding: list[float]) -> None:
        from chamados.models import EmbeddingCache
        try:
            EmbeddingCache.objects.update_or_create(
                texto_hash=texto_hash,
                modelo=self.model,
                defaults={'embedding_vector': embedding}
            )
        except Exception as e:
            logger.warning(f"Erro ao salvar cache: {e}")

    def gerar_embedding(self, texto: str, use_cache: bool = True) -> tuple[list[float], str]:
        texto_truncado = texto[:8000]
        texto_hash = self._calcular_hash(texto_truncado)

        if use_cache:
            cached = self._buscar_cache(texto_hash)
            if cached:
                return cached, texto_hash

        if not self.embeddings:
            return [], texto_hash

        try:
            embedding = self.embeddings.embed_query(texto_truncado)
            if use_cache and embedding:
                self._salvar_cache(texto_hash, embedding)
            return embedding, texto_hash
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            return [], texto_hash

    def calcular_similaridade(self, embedding1: list[float], embedding2: list[float]) -> float:
        if not embedding1 or not embedding2:
            return 0.0
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Erro ao calcular similaridade: {e}")
            return 0.0

    def buscar_similares(self, chamado_id: int, embedding: list[float]) -> SimilaridadeResult:
        from chamados.models import Chamado, EmbeddingChamado

        if not embedding:
            return SimilaridadeResult(chamado_similar_id=None, similaridade_score=0.0, is_recorrente=False)

        try:
            chamados_resolvidos = EmbeddingChamado.objects.filter(
                chamado__status__in=["resolvido", "fechado"]
            ).exclude(chamado_id=chamado_id).select_related("chamado")

            melhor_score = 0.0
            chamado_similar_id = None

            for embed_obj in chamados_resolvidos:
                score = self.calcular_similaridade(embedding, embed_obj.embedding_vector)
                if score > melhor_score:
                    melhor_score = score
                    chamado_similar_id = embed_obj.chamado_id

            is_recorrente = melhor_score >= self.threshold

            return SimilaridadeResult(
                chamado_similar_id=chamado_similar_id if is_recorrente else None,
                similaridade_score=melhor_score,
                is_recorrente=is_recorrente,
            )
        except Exception as e:
            logger.error(f"Erro ao buscar chamados similares: {e}")
            return SimilaridadeResult(chamado_similar_id=None, similaridade_score=0.0, is_recorrente=False)


def processar_chamado_completo(chamado_id: int) -> dict:
    """
    Processa um chamado com IA: classifica (Grok) e busca similares (embeddings).
    """
    from chamados.models import Chamado, EmbeddingChamado, HistoricoChamado

    try:
        chamado = Chamado.objects.get(id=chamado_id)
    except Chamado.DoesNotExist:
        logger.error(f"Chamado {chamado_id} nao encontrado")
        return {"success": False, "error": "Chamado nao encontrado"}

    classifier = IAClassifierService()
    similarity = SimilarityService()

    # 1. Classificar chamado com Grok
    classificacao = classifier.classificar(chamado.assunto, chamado.descricao)

    # 2. Gerar embedding (com cache)
    texto_base = f"{chamado.assunto}\n{chamado.descricao}"
    embedding, texto_hash = similarity.gerar_embedding(texto_base)

    # 3. Buscar similares
    similares = similarity.buscar_similares(chamado.id, embedding)

    # 4. Atualizar chamado
    chamado.ia_categoria = classificacao.categoria
    chamado.ia_prioridade_sugerida = classificacao.prioridade_sugerida
    chamado.ia_resumo = classificacao.resumo
    chamado.ia_problema_principal = classificacao.problema_principal
    chamado.ia_palavras_chave = classificacao.palavras_chave
    chamado.ia_confianca = classificacao.confianca
    chamado.ia_processed = True
    chamado.ia_processed_at = timezone.now()
    chamado.is_recorrente = similares.is_recorrente
    chamado.chamado_similar_ref_id = similares.chamado_similar_id
    chamado.similaridade_score = similares.similaridade_score if similares.is_recorrente else None

    # 4.1 AUTO-APLICAR prioridade sugerida pela IA
    prioridade_auto_aplicada = False
    old_prioridade = chamado.prioridade
    if classificacao.prioridade_sugerida and chamado.prioridade != classificacao.prioridade_sugerida:
        chamado.prioridade = classificacao.prioridade_sugerida
        prioridade_auto_aplicada = True

    chamado.save()

    # 5. Salvar embedding do chamado
    if embedding:
        EmbeddingChamado.objects.update_or_create(
            chamado=chamado,
            defaults={
                "embedding_vector": embedding,
                "texto_base": texto_base[:1000],
                "texto_hash": texto_hash,
                "modelo": settings.IA_EMBEDDING_MODEL,
            }
        )

    # 6. Registrar no historico
    descricao_historico = (
        f"Chamado processado por IA (LangChain + xAI Grok/{settings.XAI_MODEL}). "
        f"Categoria: {classificacao.categoria}, Prioridade sugerida: {classificacao.prioridade_sugerida}"
    )
    if classificacao.is_financeiro_urgente:
        descricao_historico += " (Detectado como financeiro - prioridade URGENTE)"
    if similares.is_recorrente:
        descricao_historico += f" (Chamado recorrente - similaridade: {similares.similaridade_score:.2%})"

    HistoricoChamado.objects.create(
        chamado=chamado,
        tipo_acao=HistoricoChamado.TipoAcao.RESPOSTA_IA,
        descricao=descricao_historico,
    )

    if prioridade_auto_aplicada:
        descricao_prioridade = f"Prioridade alterada automaticamente pela IA (Grok): {old_prioridade} -> {classificacao.prioridade_sugerida}"
        if classificacao.is_financeiro_urgente:
            descricao_prioridade += " (detectado como chamado financeiro)"
        HistoricoChamado.objects.create(
            chamado=chamado,
            tipo_acao=HistoricoChamado.TipoAcao.PRIORIDADE_ALTERADA,
            descricao=descricao_prioridade,
            valor_anterior=old_prioridade,
            valor_novo=classificacao.prioridade_sugerida,
        )

    return {
        "success": True,
        "chamado_id": chamado_id,
        "classificacao": {
            "categoria": classificacao.categoria,
            "prioridade_sugerida": classificacao.prioridade_sugerida,
            "resumo": classificacao.resumo,
            "confianca": classificacao.confianca,
            "is_financeiro_urgente": classificacao.is_financeiro_urgente,
        },
        "similaridade": {
            "is_recorrente": similares.is_recorrente,
            "chamado_similar_id": similares.chamado_similar_id,
            "score": similares.similaridade_score,
        },
        "prioridade_auto_aplicada": prioridade_auto_aplicada,
    }
