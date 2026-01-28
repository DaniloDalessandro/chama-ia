interface RequestOptions extends RequestInit {
  skipAuth?: boolean
}

class ApiClient {
  private getAccessToken(): string | null {
    if (typeof window === "undefined") return null
    return localStorage.getItem("access_token")
  }

  private async refreshToken(): Promise<boolean> {
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
      document.cookie = `access_token=${data.access}; path=/`

      if (data.refresh) {
        localStorage.setItem("refresh_token", data.refresh)
        document.cookie = `refresh_token=${data.refresh}; path=/`
      }

      return true
    } catch {
      return false
    }
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { skipAuth = false, ...fetchOptions } = options

    const headers = new Headers(fetchOptions.headers)

    if (!skipAuth) {
      const token = this.getAccessToken()
      if (token) {
        headers.set("Authorization", `Bearer ${token}`)
      }
    }

    if (!headers.has("Content-Type") && fetchOptions.body) {
      headers.set("Content-Type", "application/json")
    }

    const url = endpoint.startsWith("http") ? endpoint : `/api/v1${endpoint}`

    let response = await fetch(url, {
      ...fetchOptions,
      headers,
    })

    if (response.status === 401 && !skipAuth) {
      const refreshed = await this.refreshToken()

      if (refreshed) {
        const newToken = this.getAccessToken()
        if (newToken) {
          headers.set("Authorization", `Bearer ${newToken}`)
        }

        response = await fetch(url, {
          ...fetchOptions,
          headers,
        })
      } else {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        localStorage.removeItem("user")
        document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
        document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
        window.location.href = "/login"
        throw new Error("Sessão expirada")
      }
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Erro na requisição" }))
      throw new Error(error.detail || `HTTP error! status: ${response.status}`)
    }

    if (response.status === 204) {
      return null as T
    }

    return response.json()
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" })
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "DELETE" })
  }
}

export const apiClient = new ApiClient()
