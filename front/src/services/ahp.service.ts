/**
 * Serviço de administração AHP -- CRUD de Criterio/Termo/Intensidade/
 * FaixaTempoEspera e ciclo de vida de VersaoAHP. Endpoints sem barra final
 * (SimpleRouter trailing_slash=False no backend).
 */
import { apiClient } from "@/lib/api/client"
import type {
  ComparacaoPar,
  ComparacaoSubmitResult,
  Criterio,
  EstadoVersaoAHP,
  FaixaTempoEspera,
  Intensidade,
  Termo,
  ValidarVersaoResult,
  VersaoAHP,
} from "@/types/ahp"

export interface ApiResponse<T> {
  success: boolean
  message?: string
  data?: T
  errors?: Record<string, string[]>
}

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

export const ahpService = {
  // --- Critério ---
  async listCriterios(): Promise<Criterio[]> {
    return apiClient.get<Criterio[]>("/ahp/criterios")
  },
  async getCriterio(id: number): Promise<Criterio> {
    return apiClient.get<Criterio>(`/ahp/criterios/${id}`)
  },
  async createCriterio(data: Partial<Criterio>): Promise<ApiResponse<Criterio>> {
    return asApiResponse(() => apiClient.post<Criterio>("/ahp/criterios", data))
  },
  async updateCriterio(id: number, data: Partial<Criterio>): Promise<ApiResponse<Criterio>> {
    return asApiResponse(() => apiClient.patch<Criterio>(`/ahp/criterios/${id}`, data))
  },
  async deleteCriterio(id: number): Promise<ApiResponse<void>> {
    return asApiResponse(() => apiClient.delete<void>(`/ahp/criterios/${id}`))
  },
  async inativarCriterio(id: number): Promise<ApiResponse<Criterio>> {
    return asApiResponse(() => apiClient.post<Criterio>(`/ahp/criterios/${id}/inativar`))
  },
  async duplicarCriterio(id: number): Promise<ApiResponse<Criterio>> {
    return asApiResponse(() => apiClient.post<Criterio>(`/ahp/criterios/${id}/duplicar`))
  },
  async getCriterioHistorico(id: number): Promise<{
    criado_em: string
    atualizado_em: string
    atualizado_por: string | null
    versoes_ahp_participadas: VersaoAHP[]
  }> {
    return apiClient.get(`/ahp/criterios/${id}/historico`)
  },

  // --- Intensidade ---
  async listIntensidades(criterioId?: number): Promise<Intensidade[]> {
    const query = criterioId ? `?criterio=${criterioId}` : ""
    return apiClient.get<Intensidade[]>(`/ahp/intensidades${query}`)
  },
  async createIntensidade(data: Partial<Intensidade>): Promise<ApiResponse<Intensidade>> {
    return asApiResponse(() => apiClient.post<Intensidade>("/ahp/intensidades", data))
  },
  async updateIntensidade(id: number, data: Partial<Intensidade>): Promise<ApiResponse<Intensidade>> {
    return asApiResponse(() => apiClient.patch<Intensidade>(`/ahp/intensidades/${id}`, data))
  },
  async deleteIntensidade(id: number): Promise<ApiResponse<void>> {
    return asApiResponse(() => apiClient.delete<void>(`/ahp/intensidades/${id}`))
  },

  // --- FaixaTempoEspera ---
  async listFaixasTempoEspera(): Promise<FaixaTempoEspera[]> {
    return apiClient.get<FaixaTempoEspera[]>("/ahp/faixas-tempo-espera")
  },
  async createFaixaTempoEspera(data: Partial<FaixaTempoEspera>): Promise<ApiResponse<FaixaTempoEspera>> {
    return asApiResponse(() => apiClient.post<FaixaTempoEspera>("/ahp/faixas-tempo-espera", data))
  },
  async updateFaixaTempoEspera(
    id: number,
    data: Partial<FaixaTempoEspera>
  ): Promise<ApiResponse<FaixaTempoEspera>> {
    return asApiResponse(() => apiClient.patch<FaixaTempoEspera>(`/ahp/faixas-tempo-espera/${id}`, data))
  },
  async deleteFaixaTempoEspera(id: number): Promise<ApiResponse<void>> {
    return asApiResponse(() => apiClient.delete<void>(`/ahp/faixas-tempo-espera/${id}`))
  },

  // --- Termo ---
  async listTermos(criterioId?: number): Promise<Termo[]> {
    const query = criterioId ? `?criterio=${criterioId}` : ""
    return apiClient.get<Termo[]>(`/ahp/termos${query}`)
  },
  async createTermo(data: Partial<Termo>): Promise<ApiResponse<Termo>> {
    return asApiResponse(() => apiClient.post<Termo>("/ahp/termos", data))
  },
  async updateTermo(id: number, data: Partial<Termo>): Promise<ApiResponse<Termo>> {
    return asApiResponse(() => apiClient.patch<Termo>(`/ahp/termos/${id}`, data))
  },
  async deleteTermo(id: number): Promise<ApiResponse<void>> {
    return asApiResponse(() => apiClient.delete<void>(`/ahp/termos/${id}`))
  },
  async aprovarTermo(id: number): Promise<ApiResponse<Termo>> {
    return asApiResponse(() => apiClient.post<Termo>(`/ahp/termos/${id}/aprovar`))
  },
  async rejeitarTermo(id: number): Promise<ApiResponse<Termo>> {
    return asApiResponse(() => apiClient.post<Termo>(`/ahp/termos/${id}/rejeitar`))
  },

  // --- VersaoAHP ---
  async listVersoes(): Promise<VersaoAHP[]> {
    return apiClient.get<VersaoAHP[]>("/ahp/versoes-ahp")
  },
  async getVersaoAtiva(): Promise<VersaoAHP | null> {
    try {
      return await apiClient.get<VersaoAHP>("/ahp/versoes-ahp/ativa")
    } catch {
      // Único modo de falha deste endpoint no contrato é 404 (nenhuma versão
      // ativa) -- apiClient não expõe o status HTTP no erro lançado, então
      // qualquer falha aqui é tratada como "nenhuma versão ativa".
      return null
    }
  },
  async createVersao(descricao: string): Promise<ApiResponse<VersaoAHP>> {
    return asApiResponse(() => apiClient.post<VersaoAHP>("/ahp/versoes-ahp", { descricao }))
  },
  async updateVersao(id: number, descricao: string): Promise<ApiResponse<VersaoAHP>> {
    return asApiResponse(() => apiClient.patch<VersaoAHP>(`/ahp/versoes-ahp/${id}`, { descricao }))
  },
  async submitComparacoesCriterios(
    versaoId: number,
    pares: ComparacaoPar[]
  ): Promise<ApiResponse<ComparacaoSubmitResult>> {
    return asApiResponse(() =>
      apiClient.post<ComparacaoSubmitResult>(`/ahp/versoes-ahp/${versaoId}/comparacoes-criterios`, pares)
    )
  },
  async submitComparacoesIntensidades(
    versaoId: number,
    criterioCodigo: string,
    pares: ComparacaoPar[]
  ): Promise<ApiResponse<ComparacaoSubmitResult>> {
    return asApiResponse(() =>
      apiClient.post<ComparacaoSubmitResult>(
        `/ahp/versoes-ahp/${versaoId}/comparacoes-intensidades/${criterioCodigo}`,
        pares
      )
    )
  },
  async validarVersao(versaoId: number): Promise<ValidarVersaoResult> {
    return apiClient.post<ValidarVersaoResult>(`/ahp/versoes-ahp/${versaoId}/validar`)
  },

  /**
   * `apiClient` lança e descarta o corpo da resposta em qualquer status
   * não-ok, mas o backend devolve 200 (ativa) OU 422 (inconsistente/erro)
   * -- em ambos os casos com o corpo completo da VersaoAHP (estado +
   * mensagens_erro), que precisamos ler mesmo no caminho de erro. Por isso
   * este método usa fetch bruto (com o mesmo token de `apiClient`) em vez do
   * wrapper padrão -- única exceção deliberada à convenção "services usam
   * apiClient diretamente".
   */
  async ativarVersao(
    versaoId: number
  ): Promise<
    | { success: true; data: VersaoAHP }
    | { success: false; estado: EstadoVersaoAHP | null; mensagens_erro: string[] }
  > {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null
    const response = await fetch(`/api/v1/ahp/versoes-ahp/${versaoId}/ativar`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })
    const data = await response.json().catch(() => null)

    if (response.ok) {
      return { success: true, data: data as VersaoAHP }
    }
    return {
      success: false,
      estado: data?.estado ?? null,
      mensagens_erro: data?.mensagens_erro ?? [],
    }
  },
}
