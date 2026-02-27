export interface ChamadoCreateData {
  nome: string
  email: string
  telefone?: string
  tipo: string
  assunto: string
  descricao: string
  anexos?: File[]
}

export interface ChamadoCreateResponse {
  id: number
  protocolo: string
  status: string
  created_at: string
}

export interface SolucaoSimilar {
  id: number
  protocolo: string
  assunto: string
  status: string
  ia_resumo: string | null
  resolved_at: string | null
  comentarios_publicos: {
    id: string
    conteudo: string
    autor_nome: string
    created_at: string
  }[]
}

export interface IAProcessamentoResponse {
  id: number
  protocolo: string
  status: string
  ia_processed: boolean
  ia_categoria: string | null
  ia_prioridade_sugerida: string | null
  ia_resumo: string | null
  ia_confianca: number | null
  is_recorrente: boolean
  similaridade_score: number | null
  solucao_similar: SolucaoSimilar | null
}

export interface ChamadoConsultaResponse {
  protocolo: string
  assunto: string
  status: string
  status_display: string
  created_at: string
  updated_at: string
  resolved_at: string | null
  comentarios_publicos: {
    id: string
    conteudo: string
    autor_nome: string
    created_at: string
  }[]
}

export interface ChamadoConsultaProtocoloResponse {
  protocolo: string
  assunto: string
  descricao: string
  tipo: string
  tipo_display: string
  status: string
  status_display: string
  prioridade: string
  prioridade_display: string
  created_at: string
  updated_at: string
  resolved_at: string | null
  comentarios_publicos: {
    id: string
    tipo: string
    conteudo: string
    autor_nome: string
    is_from_client: boolean
    created_at: string
  }[]
  anexos: {
    id: string
    nome_original: string
    tipo: string
    tamanho: number
    url: string | null
    created_at: string
  }[]
  historico_publico: {
    id: string
    tipo_acao: string
    tipo_acao_display: string
    descricao: string
    created_at: string
  }[]
}

export interface ChamadoResumoEmail {
  id: number
  protocolo: string
  assunto: string
  status: string
  status_display: string
  created_at: string
  updated_at: string
}

export interface ChamadoListaEmailResponse {
  total: number
  data: ChamadoResumoEmail[]
}

export interface ApiResponse<T> {
  success: boolean
  message: string
  data?: T
  errors?: Record<string, string[]>
}

const API_BASE = "/api/v1/chamados"

export const chamadoService = {
  /**
   * Criar novo chamado (endpoint publico) - retorno rapido sem IA
   */
  async create(data: ChamadoCreateData): Promise<ApiResponse<ChamadoCreateResponse>> {
    const formData = new FormData()

    formData.append("nome", data.nome)
    formData.append("email", data.email)
    if (data.telefone) formData.append("telefone", data.telefone)
    formData.append("tipo", data.tipo)
    formData.append("assunto", data.assunto)
    formData.append("descricao", data.descricao)

    // Adicionar anexos
    if (data.anexos && data.anexos.length > 0) {
      data.anexos.forEach((file) => {
        formData.append("anexos", file)
      })
    }

    const response = await fetch(`${API_BASE}/publico/`, {
      method: "POST",
      body: formData,
    })

    return response.json()
  },

  /**
   * Processar chamado com IA (segunda fase - busca similar + classificacao)
   */
  async processarIA(chamadoId: number): Promise<ApiResponse<IAProcessamentoResponse>> {
    const response = await fetch(`${API_BASE}/publico/${chamadoId}/processar-ia`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })

    if (!response.ok) {
      return {
        success: false,
        message: `Erro no processamento IA (${response.status})`,
      }
    }

    return response.json()
  },

  /**
   * Consultar chamado por protocolo e email (endpoint publico)
   */
  async consultar(protocolo: string, email: string): Promise<ApiResponse<ChamadoConsultaResponse>> {
    const params = new URLSearchParams({ protocolo, email })
    const response = await fetch(`${API_BASE}/publico/consulta/?${params}`)
    return response.json()
  },

  /**
   * Consultar chamado detalhado por protocolo (endpoint publico)
   */
  async consultarPorProtocolo(protocolo: string): Promise<ApiResponse<ChamadoConsultaProtocoloResponse>> {
    const params = new URLSearchParams({ protocolo })
    const response = await fetch(`${API_BASE}/publico/consulta-protocolo/?${params}`)
    return response.json()
  },

  /**
   * Listar todos os chamados de um e-mail (endpoint publico)
   */
  async listarPorEmail(email: string): Promise<ApiResponse<ChamadoResumoEmail[]> & { total?: number }> {
    const params = new URLSearchParams({ email })
    const response = await fetch(`${API_BASE}/publico/consulta-email/?${params}`)
    return response.json()
  },
}

// Alias para manter compatibilidade
export const ticketService = chamadoService
