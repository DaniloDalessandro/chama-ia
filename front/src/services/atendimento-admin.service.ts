/**
 * Serviço staff (autenticado) de Atendimento -- fila, detalhe, ações de
 * classificação/revisão/encaminhamento e chat via fallback REST.
 * Endpoints sem barra final (SimpleRouter trailing_slash=False no backend).
 */
import { apiClient } from "@/lib/api/client"
import type {
  Atendimento,
  AtendimentoDetalhe,
  AtendimentoFilaCard,
  AuditoriaClassificacaoSummary,
  AvaliacaoCriterioAtendimento,
  MensagemAtendimento,
  RevisaoHumanaAtendimento,
} from "@/types/atendimento"

export interface ApiResponse<T> {
  success: boolean
  message?: string
  data?: T
  errors?: Record<string, string[]>
}

interface ChamadoResumo {
  id: number
  protocolo: string
  status: string
  status_display: string
}

const API_BASE = "/atendimento/atendimentos"

async function asApiResponse<T>(fn: () => Promise<T>): Promise<ApiResponse<T>> {
  try {
    const data = await fn()
    return { success: true, data }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : "Erro inesperado",
    }
  }
}

export const atendimentoAdminService = {
  async list(): Promise<Atendimento[]> {
    return apiClient.get<Atendimento[]>(API_BASE)
  },

  async getFila(): Promise<AtendimentoFilaCard[]> {
    return apiClient.get<AtendimentoFilaCard[]>(`${API_BASE}/fila`)
  },

  async getDetalhe(id: number): Promise<AtendimentoDetalhe> {
    return apiClient.get<AtendimentoDetalhe>(`${API_BASE}/${id}/detalhe`)
  },

  async get(id: number): Promise<Atendimento> {
    return apiClient.get<Atendimento>(`${API_BASE}/${id}`)
  },

  async update(id: number, data: Partial<Atendimento>): Promise<Atendimento> {
    return apiClient.patch<Atendimento>(`${API_BASE}/${id}`, data)
  },

  async classificar(id: number): Promise<ApiResponse<AuditoriaClassificacaoSummary>> {
    return asApiResponse(() =>
      apiClient.post<AuditoriaClassificacaoSummary>(`${API_BASE}/${id}/classificar`)
    )
  },

  async revisaoHumana(
    id: number,
    payload: { nova_prioridade: string; justificativa: string }
  ): Promise<ApiResponse<RevisaoHumanaAtendimento>> {
    return asApiResponse(() =>
      apiClient.post<RevisaoHumanaAtendimento>(`${API_BASE}/${id}/revisao-humana`, payload)
    )
  },

  async encaminharChamado(
    id: number,
    payload: { motivo: string }
  ): Promise<ApiResponse<ChamadoResumo>> {
    return asApiResponse(() =>
      apiClient.post<ChamadoResumo>(`${API_BASE}/${id}/encaminhar-chamado`, payload)
    )
  },

  async getMensagens(id: number): Promise<MensagemAtendimento[]> {
    return apiClient.get<MensagemAtendimento[]>(`${API_BASE}/${id}/mensagens`)
  },

  async sendMensagem(id: number, conteudo: string): Promise<MensagemAtendimento> {
    return apiClient.post<MensagemAtendimento>(`${API_BASE}/${id}/mensagens`, {
      remetente_tipo: "atendente",
      conteudo,
    })
  },

  async getAvaliacoes(id: number): Promise<AvaliacaoCriterioAtendimento[]> {
    return apiClient.get<AvaliacaoCriterioAtendimento[]>(`${API_BASE}/${id}/avaliacoes`)
  },

  async upsertAvaliacao(
    id: number,
    payload: {
      criterio: number
      intensidade: number
      evidencia?: string
      justificativa?: string
      confianca?: number
    }
  ): Promise<ApiResponse<AvaliacaoCriterioAtendimento>> {
    return asApiResponse(() =>
      apiClient.post<AvaliacaoCriterioAtendimento>(`${API_BASE}/${id}/avaliacoes`, payload)
    )
  },
}
