import { setAuthTokens } from '@/lib/cookies'

export interface User {
  id: number
  email: string
  name: string
  role: 'admin' | 'atendente' | 'cliente'
  role_display: string
  cpf?: string
  phone?: string
  avatar?: string
  is_active: boolean
  is_staff: boolean
  created_at: string
  updated_at: string
}

export interface UserCreate {
  email: string
  name: string
  role: 'admin' | 'atendente' | 'cliente'
  cpf?: string
  phone?: string
  password: string
  password_confirm: string
  is_active?: boolean
  is_staff?: boolean
}

export interface UserUpdate {
  name?: string
  role?: 'admin' | 'atendente' | 'cliente'
  cpf?: string
  phone?: string
  avatar?: string
  is_active?: boolean
  is_staff?: boolean
}

export interface UserStats {
  total: number
  ativos: number
  inativos: number
  por_role: {
    [key: string]: {
      label: string
      count: number
    }
  }
}

const API_BASE = "/api/v1/accounts/usuarios"

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

const userService = {
  // Listar todos os usuários
  list: async (params?: {
    search?: string
    role?: string
    is_active?: boolean
  }) => {
    const queryParams = new URLSearchParams()
    if (params?.search) queryParams.append("search", params.search)
    if (params?.role) queryParams.append("role", params.role)
    if (params?.is_active !== undefined) queryParams.append("is_active", String(params.is_active))

    const url = `${API_BASE}/${queryParams.toString() ? `?${queryParams.toString()}` : ""}`
    return apiRequest<User[]>(url)
  },

  // Buscar usuário por ID
  get: async (id: number) => {
    return apiRequest<User>(`${API_BASE}/${id}/`)
  },

  // Criar novo usuário
  create: async (data: UserCreate) => {
    return apiRequest<User>(`${API_BASE}/`, {
      method: "POST",
      body: JSON.stringify(data),
    })
  },

  // Atualizar usuário
  update: async (id: number, data: UserUpdate) => {
    return apiRequest<User>(`${API_BASE}/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    })
  },

  // Remover usuário
  delete: async (id: number) => {
    return apiRequest<void>(`${API_BASE}/${id}/`, {
      method: "DELETE",
    })
  },

  // Alternar status ativo/inativo
  toggleActive: async (id: number) => {
    return apiRequest<User>(`${API_BASE}/${id}/toggle_active/`, {
      method: "POST",
    })
  },

  // Resetar senha de um usuário (admin)
  resetPassword: async (id: number, newPassword: string) => {
    return apiRequest<{ detail: string }>(`${API_BASE}/${id}/reset_password/`, {
      method: "POST",
      body: JSON.stringify({ new_password: newPassword }),
    })
  },

  // Estatísticas de usuários
  stats: async () => {
    return apiRequest<UserStats>(`${API_BASE}/stats/`)
  },
}

export default userService
