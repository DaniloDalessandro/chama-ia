/**
 * Tipos compartilhados do domínio Atendimento (chat/fila priorizada).
 * Espelham exatamente os serializers de `backend/atendimento/serializers.py`.
 */

export type StatusAtendimento =
  | "aguardando"
  | "em_atendimento"
  | "aguardando_cliente"
  | "resolvido"
  | "cancelado"
  | "encaminhado_para_chamado"

export type Prioridade =
  | "nao_classificado"
  | "p1"
  | "p2"
  | "p3"
  | "p4"
  | "revisao_humana"

export type AnaliseIAStatus = "pendente" | "processando" | "concluida" | "erro"

export type OrigemAtendimento = "chat" | "email"

export type RemetenteTipo = "cliente" | "atendente" | "sistema"

export interface Atendimento {
  id: number
  session_token: string
  origem: OrigemAtendimento
  status_atendimento: StatusAtendimento
  prioridade: Prioridade
  analise_ia_status: AnaliseIAStatus
  indice_ahp: number | null
  regra_critica_confirmada: boolean
  versao_ahp_utilizada: number | null
  assunto: string
  resumo: string
  servico_afetado: string
  atendente: number | null
  nome: string
  email: string
  telefone: string
  cliente: number | null
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
}

export interface MensagemAtendimento {
  id: number
  atendimento: number
  remetente_tipo: RemetenteTipo
  conteudo: string
  criado_em: string
}

export interface AnexoAtendimento {
  id: string
  atendimento: number
  arquivo: string
  nome_original: string
  tipo_arquivo: "pdf" | "imagem" | "documento" | "outro"
  tamanho: number
  mime_type: string
  criado_em: string
}

export interface AvaliacaoCriterioAtendimento {
  id: number
  atendimento: number
  criterio: number
  intensidade: number
  evidencia: string
  justificativa: string
  origem: "manual" | "agente_avaliacao" | "tempo_espera_service"
  confianca: number | null
  dados_ausentes: boolean
  criado_em: string
  criado_por: number | null
  atualizado_em: string
  atualizado_por: number | null
}

/**
 * Subconjunto seguro para a UI: `AuditoriaClassificacao` no backend carrega
 * pesos/matrizes/CI/CR/lambda_max -- nunca devem ser renderizados (nem para
 * staff). Só existência/timestamp são consumidos, por isso o tipo no
 * frontend só expõe esses campos -- impossível acessar os demais por erro.
 */
export interface AuditoriaClassificacaoSummary {
  id: number
  atendimento: number
  criado_em: string
}

export interface RegraCriticaAtendimento {
  id: number
  atendimento: number
  criterio_gatilho: number | null
  termo_gatilho: number | null
  confirmada: boolean
  justificativa: string
  origem: "manual" | "agente_validacao_critica"
  criado_em: string
}

export interface RevisaoHumanaAtendimento {
  id: number
  atendimento: number
  prioridade_anterior: string
  nova_prioridade: string
  responsavel: number
  justificativa: string
  criado_em: string
}

export interface ChamadoRelacionado {
  id: number
  protocolo: string
  status: string
  status_display: string
  assunto: string
}

export interface AtendimentoFilaCard {
  id: number
  nome: string
  cliente: number | null
  assunto: string
  resumo: string
  servico_afetado: string
  prioridade: Prioridade
  indice_ahp: number | null
  analise_ia_status: AnaliseIAStatus
  tempo_espera_minutos: number
  sla: null
  atendente: { id: number; name: string } | null
  anexos_count: number
  dados_ausentes: boolean
  regra_critica_confirmada: boolean
  status_atendimento: StatusAtendimento
  criado_em: string
}

export interface AtendimentoDetalhe {
  atendimento: Atendimento
  conversa: MensagemAtendimento[]
  anexos: AnexoAtendimento[]
  avaliacoes_criterios: AvaliacaoCriterioAtendimento[]
  auditoria_mais_recente: AuditoriaClassificacaoSummary | null
  regra_critica: RegraCriticaAtendimento | null
  revisoes_humanas: RevisaoHumanaAtendimento[]
  chamado_relacionado: ChamadoRelacionado | null
}

export interface AtendimentoPublicoCreateResponse {
  id: number
  session_token: string
  nome: string
  email: string
  telefone: string | null
  status_atendimento: StatusAtendimento
  analise_ia_status: AnaliseIAStatus
  criado_em: string
}

export interface AtendimentoPublicoStatus {
  id: number
  nome: string
  assunto: string
  resumo: string
  servico_afetado: string
  prioridade: Prioridade
  indice_ahp: number | null
  analise_ia_status: AnaliseIAStatus
  tempo_espera_minutos: number
  sla: null
  status_atendimento: StatusAtendimento
  criado_em: string
}

// --- Envelopes do WebSocket (ws/atendimento/<id>/?token=<token>) ---

export interface WsConnectionEstablished {
  type: "connection_established"
  atendimento: {
    id: number
    status_atendimento: StatusAtendimento
    analise_ia_status: AnaliseIAStatus
    prioridade: Prioridade
  }
}

export interface WsChatMessage {
  type: "chat_message"
  mensagem: MensagemAtendimento
}

export interface WsTyping {
  type: "typing"
  remetente_tipo: "cliente" | "atendente"
  sender_label: string
}

export interface WsStaffJoined {
  type: "staff_joined"
  atendente: { id: number; name: string }
}

export interface WsStaffLeft {
  type: "staff_left"
  atendente: { id: number; name: string }
}

export interface WsAnaliseStatusChanged {
  type: "analise_status_changed"
  analise_ia_status?: AnaliseIAStatus
  prioridade?: Prioridade
  indice_ahp?: number | null
}

export interface WsPong {
  type: "pong"
  timestamp: unknown
}

export interface WsError {
  type: "error"
  message: string
}

export type AtendimentoWsEnvelope =
  | WsConnectionEstablished
  | WsChatMessage
  | WsTyping
  | WsStaffJoined
  | WsStaffLeft
  | WsAnaliseStatusChanged
  | WsPong
  | WsError
