import { setAuthTokens } from '@/lib/cookies'

export interface Cliente {
  id: number
  nome: string
  nome_fantasia: string
  cnpj: string
  nome_responsavel: string
  email?: string
  telefone?: string
  endereco?: string
  ativo: boolean
  created_at: string
  updated_at: string
  created_by?: number
  created_by_name?: string
  updated_by?: number
  updated_by_name?: string
}

export interface ClienteCreate {
  nome: string
  nome_fantasia?: string
  cnpj: string
  nome_responsavel: string
  email?: string
  telefone?: string
  endereco?: string
  ativo?: boolean
}

const API_BASE = "/api/v1/clientes"

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

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  let response = await fetch(endpoint, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  })

  if (response.status === 401) {
    const refreshed = await refreshToken()
    if (refreshed) {
      response = await fetch(endpoint, {
        ...options,
        headers: {
          ...getAuthHeaders(),
          ...options.headers,
        },
      })
    } else {
      localStorage.removeItem("access_token")
      localStorage.removeItem("refresh_token")
      window.location.href = "/login"
      throw new Error("Sessão expirada")
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw { response: { data: errorData }, status: response.status }
  }

  return response.json()
}

const clienteService = {
  // Listar todos os clientes
  list: async (params?: {
    search?: string
    ativo?: boolean
  }) => {
    const queryParams = new URLSearchParams()
    if (params?.search) queryParams.append("search", params.search)
    if (params?.ativo !== undefined) queryParams.append("ativo", String(params.ativo))

    const url = `${API_BASE}/${queryParams.toString() ? `?${queryParams.toString()}` : ""}`
    return apiRequest<Cliente[]>(url)
  },

  // Listar apenas clientes ativos
  listAtivos: async () => {
    return apiRequest<Cliente[]>(`${API_BASE}/ativos/`)
  },

  // Buscar cliente por ID
  get: async (id: number) => {
    return apiRequest<Cliente>(`${API_BASE}/${id}/`)
  },

  // Criar novo cliente
  create: async (data: ClienteCreate) => {
    return apiRequest<Cliente>(API_BASE + "/", {
      method: "POST",
      body: JSON.stringify(data),
    })
  },

  // Atualizar cliente
  update: async (id: number, data: Partial<ClienteCreate>) => {
    return apiRequest<Cliente>(`${API_BASE}/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  },

  // Atualizar parcialmente
  patch: async (id: number, data: Partial<ClienteCreate>) => {
    return apiRequest<Cliente>(`${API_BASE}/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  },

  // Remover cliente
  delete: async (id: number) => {
    return apiRequest<void>(`${API_BASE}/${id}/`, {
      method: "DELETE",
    })
  },

  // Alternar status ativo/inativo
  toggleAtivo: async (id: number) => {
    return apiRequest<Cliente>(`${API_BASE}/${id}/toggle_ativo/`, {
      method: "POST",
    })
  },
}

export default clienteService
