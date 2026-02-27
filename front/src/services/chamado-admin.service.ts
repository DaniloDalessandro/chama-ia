/**
 * Servico para gerenciamento de chamados (area administrativa)
 */
import { setAuthTokens } from '@/lib/cookies'

export interface Chamado {
  id: number
  protocolo: string
  nome: string
  email: string
  tipo: string
  tipo_display: string
  assunto: string
  descricao: string
  status: string
  status_display: string
  status_kanban: "novo" | "em_andamento" | "concluido"
  status_kanban_display: string
  prioridade: string
  prioridade_display: string
  origem: string
  origem_display: string
  atendente_nome: string | null
  created_by_nome: string | null
  updated_by_nome: string | null
  total_anexos: number
  total_comentarios: number
  created_at: string
  updated_at: string
  resolved_at: string | null
  // Campos IA
  ia_processed: boolean
  ia_categoria: string
  ia_prioridade_sugerida: string
  ia_resumo: string
  ia_confianca: number
  is_recorrente: boolean
  chamado_similar_ref: number | null
  chamado_similar_protocolo: string | null
  similaridade_score: number | null
}

export interface ChamadoSimilar {
  id: number
  protocolo: string
  assunto: string
  status: string
  resolved_at: string | null
}

export interface ChamadoDetail extends Chamado {
  telefone: string
  ip_address: string
  user_agent: string
  usuario_nome: string | null
  chat_session_id: string
  ia_response: string
  resolved_at: string | null
  closed_at: string | null
  anexos: Anexo[]
  historico: Historico[]
  comentarios: Comentario[]
  // Campos IA detalhados
  ia_problema_principal: string
  ia_palavras_chave: string[]
  ia_processed_at: string | null
  chamado_similar: ChamadoSimilar | null
}

export interface Anexo {
  id: string
  nome_original: string
  tipo: string
  tamanho: number
  mime_type: string
  url: string
  created_at: string
}

export interface Historico {
  id: string
  tipo_acao: string
  tipo_acao_display: string
  descricao: string
  valor_anterior: string
  valor_novo: string
  usuario_nome: string | null
  created_at: string
}

export interface Comentario {
  id: string
  tipo: string
  tipo_display: string
  conteudo: string
  autor_nome: string
  is_from_client: boolean
  created_at: string
}

export interface ChamadosResponse {
  success?: boolean
  results?: Chamado[]
  count?: number
  next?: string | null
  previous?: string | null
}

export interface ApiResponse<T> {
  success: boolean
  message?: string
  data?: T
  errors?: Record<string, string[]>
}

const API_BASE = "/api/v1/chamados"

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token")
  return {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
  }
}

async function refreshToken(): Promise<boolean> {
  const refresh = localStorage.getItem("refresh_token")
  if (!refresh) return false

  try {
    const response = await fetch("/api/v1/accounts/token/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })

    if (!response.ok) return false

    const data = await response.json()
    localStorage.setItem("access_token", data.access)
    setAuthTokens(data.access, data.refresh)
    if (data.refresh) {
      localStorage.setItem("refresh_token", data.refresh)
    }
    return true
  } catch {
    return false
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, {
    ...options,
    headers: { ...getAuthHeaders(), ...(options.headers || {}) },
  })

  if (response.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      return fetch(url, {
        ...options,
        headers: { ...getAuthHeaders(), ...(options.headers || {}) },
      })
    }
  }

  return response
}

export const chamadoAdminService = {
  /**
   * Listar todos os chamados
   */
  async list(params?: {
    status?: string
    status_kanban?: string
    prioridade?: string
    tipo?: string
    atendente?: string
    search?: string
    ordering?: string
    page?: number
  }): Promise<Chamado[]> {
    const searchParams = new URLSearchParams()

    if (params?.status) searchParams.append("status", params.status)
    if (params?.status_kanban) searchParams.append("status_kanban", params.status_kanban)
    if (params?.prioridade) searchParams.append("prioridade", params.prioridade)
    if (params?.tipo) searchParams.append("tipo", params.tipo)
    if (params?.atendente) searchParams.append("atendente", params.atendente)
    if (params?.search) searchParams.append("search", params.search)
    if (params?.ordering) searchParams.append("ordering", params.ordering)
    if (params?.page) searchParams.append("page", params.page.toString())

    const url = `${API_BASE}?${searchParams.toString()}`
    const response = await fetchWithAuth(url)

    if (!response.ok) {
      throw new Error("Erro ao listar chamados")
    }

    const data: ChamadosResponse = await response.json()

    // A API pode retornar { results: [...] } ou diretamente um array
    return data.results || (Array.isArray(data) ? data : [])
  },

  /**
   * Obter detalhes de um chamado
   */
  async get(id: number): Promise<ChamadoDetail> {
    const response = await fetchWithAuth(`${API_BASE}/${id}`)

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Sessao expirada. Faca login novamente.")
      }
      if (response.status === 404) {
        throw new Error("Chamado nao encontrado.")
      }
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || error.message || `Erro ao obter chamado (${response.status})`)
    }

    return response.json()
  },

  /**
   * Atualizar status Kanban (drag and drop)
   */
  async updateStatusKanban(
    id: number,
    statusKanban: "novo" | "em_andamento" | "concluido"
  ): Promise<ApiResponse<Chamado>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/status-kanban`, {
      method: "PATCH",
      body: JSON.stringify({ status_kanban: statusKanban }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao atualizar status",
        errors: error.errors,
      }
    }

    return response.json()
  },

  /**
   * Atualizar status detalhado
   */
  async updateStatus(id: number, status: string): Promise<ApiResponse<ChamadoDetail>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao atualizar status",
      }
    }

    return response.json()
  },

  /**
   * Atualizar prioridade
   */
  async updatePrioridade(id: number, prioridade: string): Promise<ApiResponse<ChamadoDetail>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/prioridade`, {
      method: "PATCH",
      body: JSON.stringify({ prioridade }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao atualizar prioridade",
      }
    }

    return response.json()
  },

  /**
   * Adicionar comentario
   */
  async addComentario(
    id: number,
    conteudo: string,
    tipo: "interno" | "publico" = "publico"
  ): Promise<ApiResponse<Comentario>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/comentario`, {
      method: "POST",
      body: JSON.stringify({ conteudo, tipo }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao adicionar comentario",
      }
    }

    return response.json()
  },

  /**
   * Obter estatisticas
   */
  async getEstatisticas(): Promise<{
    total: number
    abertos: number
    em_atendimento: number
    resolvidos_hoje: number
    criados_hoje: number
    criados_semana: number
    criados_mes: number
    por_status: { status: string; count: number }[]
    por_prioridade: { prioridade: string; count: number }[]
    por_tipo: { tipo: string; count: number }[]
  }> {
    const response = await fetchWithAuth(`${API_BASE}/estatisticas`)

    if (!response.ok) {
      throw new Error("Erro ao obter estatisticas")
    }

    const data = await response.json()
    return data.data
  },

  /**
   * Processar chamado com IA
   */
  async processarIA(id: number): Promise<ApiResponse<ChamadoDetail>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/processar-ia`, {
      method: "POST",
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao processar com IA",
      }
    }

    return response.json()
  },

  /**
   * Aplicar classificacao IA (prioridade sugerida)
   */
  async aplicarClassificacaoIA(id: number): Promise<ApiResponse<ChamadoDetail>> {
    const response = await fetchWithAuth(`${API_BASE}/${id}/aplicar-classificacao-ia`, {
      method: "POST",
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      return {
        success: false,
        message: error.message || "Erro ao aplicar classificacao IA",
      }
    }

    return response.json()
  },

  /**
   * Listar historico de chamados (concluidos ha mais de 30 dias)
   */
  async listHistorico(params?: {
    search?: string
    ordering?: string
  }): Promise<Chamado[]> {
    const searchParams = new URLSearchParams()

    if (params?.search) searchParams.append("search", params.search)
    if (params?.ordering) searchParams.append("ordering", params.ordering)

    const url = `${API_BASE}/historico?${searchParams.toString()}`
    const response = await fetchWithAuth(url)

    if (!response.ok) {
      throw new Error("Erro ao listar historico de chamados")
    }

    return response.json()
  },

  /**
   * Listar atendentes (para filtros e atribuicao)
   */
  async listAtendentes(): Promise<{ id: number; name: string; email: string; role: string }[]> {
    const response = await fetchWithAuth("/api/v1/accounts/atendentes")

    if (!response.ok) return []

    return response.json()
  },
}
