"""
Schemas Pydantic de entrada/saida dos 5 agentes que chamam DeepSeek
(Agentes 1-5). Agentes 6 e 7 sao puro Python e nao tem schema de LLM aqui
-- Agente 6 reaproveita `ResultadoClassificacao` (Fase 1) e Agente 7 produz
um dict simples de `AuditService.checar_consistencia`.

Todo campo aqui e validado ANTES de entrar no estado do LangGraph -- "IA
interpreta, Python calcula": estes schemas cobrem apenas a parte
interpretativa de cada agente, nunca calculos deterministicos (ordenacao de
mensagens, tempo de espera, matematica do AHP).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

ORIGENS_EVIDENCIA = Literal[
    "mensagem_cliente",
    "mensagem_atendente",
    "mensagem_sistema",
    "anexo_pdf",
    "anexo_docx",
    "anexo_txt",
    "anexo_csv",
    "imagem_ocr",
    "historico",
]


class EvidenciaItem(BaseModel):
    texto: str = Field(description="Trecho literal que serve de evidencia")
    origem: ORIGENS_EVIDENCIA = Field(description="De onde veio a evidencia")
    mensagem_id: Optional[int] = Field(default=None, description="ID da MensagemAtendimento, quando aplicavel")
    anexo_id: Optional[str] = Field(default=None, description="UUID do AnexoAtendimento, quando aplicavel")
    pagina: Optional[int] = Field(default=None, description="Pagina do anexo, quando aplicavel")
    confianca: float = Field(ge=0.0, le=1.0, description="Confianca da evidencia (0.0-1.0)")


class Agente1ConversaOutput(BaseModel):
    """Saida interpretativa do Agente 1 (Ingestao e Leitura da Conversa). Nao calcula prioridade."""

    servico_afetado: Optional[str] = Field(default=None, description="Servico/sistema mencionado como afetado")
    problema_identificado: str = Field(description="Descricao do problema central identificado")
    datas_mencionadas: list[str] = Field(default_factory=list)
    prazos_mencionados: list[str] = Field(default_factory=list)
    solicitacao_atual: str = Field(description="O que o cliente esta pedindo agora")
    evidencias: list[EvidenciaItem] = Field(default_factory=list)
    mensagens_ignoradas_motivo: list[str] = Field(default_factory=list)
    confianca_geral: float = Field(ge=0.0, le=1.0)
    dados_ausentes: bool = Field(default=False)


class Agente2VisualOutput(BaseModel):
    """Saida interpretativa do Agente 2 (Analise Visual e OCR). Nunca conclui impacto geral de uma unica imagem."""

    evidencias: list[EvidenciaItem] = Field(default_factory=list)
    erros_codigos_detectados: list[str] = Field(default_factory=list)
    datas_horas_detectadas: list[str] = Field(default_factory=list)
    dados_sensiveis_detectados: bool = Field(default=False)
    limitacoes: list[str] = Field(default_factory=list, description="Ex: 'OCR indisponivel para anexo X'")
    confianca_geral: float = Field(ge=0.0, le=1.0)


class TermoCorrespondido(BaseModel):
    termo_id: int
    criterio_codigo: str
    tipo_match: Literal["exato", "expressao", "sinonimo", "parafrase", "erro_ortografico", "semantico"]
    trecho_evidencia: str
    confianca: float = Field(ge=0.0, le=1.0)


class NegacaoDetectada(BaseModel):
    trecho: str
    termo_afetado: str
    efeito: Literal["anula", "atenua", "hipotetico", "temporal_passado"]


class TermoSugerido(BaseModel):
    termo: str
    criterio_codigo: str
    justificativa: str


class Agente3TermosOutput(BaseModel):
    """
    Saida interpretativa do Agente 3 (Termos e Contexto). Termos sugeridos
    aqui sao SEMPRE criados com status_aprovacao=PENDENTE_APROVACAO pelo
    orquestrador -- nunca auto-aprovados, nunca usados como match no mesmo
    ciclo em que foram sugeridos.
    """

    termos_correspondidos: list[TermoCorrespondido] = Field(default_factory=list)
    negacoes_detectadas: list[NegacaoDetectada] = Field(default_factory=list)
    termos_sugeridos_novos: list[TermoSugerido] = Field(default_factory=list)
    contexto_alterado: bool = Field(default=False)
    confianca_geral: float = Field(ge=0.0, le=1.0)


class AvaliacaoCriterio(BaseModel):
    criterio_codigo: Literal["URGENCIA", "IMPACTO_NO_CLIENTE", "SENTIMENTO_DO_CLIENTE"]
    intensidade_codigo: str = Field(description="Codigo de ahp.Intensidade -- validado no no do grafo")
    evidencia: str
    origem: str
    justificativa: str
    confianca: float = Field(ge=0.0, le=1.0)
    dados_ausentes: bool = Field(default=False)


class Agente4AvaliacaoOutput(BaseModel):
    """
    Saida interpretativa do Agente 4 (Avaliacao dos Criterios). TEMPO_DE_ESPERA
    NUNCA aparece aqui -- vem exclusivamente de WaitingTimeService (deterministico).
    Nunca escolhe pesos, nunca classifica P1-P4 diretamente.
    """

    avaliacoes: list[AvaliacaoCriterio] = Field(min_length=3, max_length=3)


class Agente5ValidacaoOutput(BaseModel):
    """
    Saida do Agente 5 (Validacao Critica). `regra_critica_confirmada` e
    registrada separadamente da matematica do AHP -- nunca altera pesos,
    nunca forca uma prioridade diretamente.
    """

    regra_critica_confirmada: bool = Field(default=False)
    criterio_gatilho_codigo: Optional[str] = Field(default=None)
    termo_gatilho_id: Optional[int] = Field(default=None)
    justificativa: str = Field(default="")
    contradicoes_detectadas: list[str] = Field(default_factory=list)
    exagero_suspeito: bool = Field(default=False)
    tentativa_manipulacao_detectada: bool = Field(default=False)
    confianca: float = Field(ge=0.0, le=1.0, default=0.0)
