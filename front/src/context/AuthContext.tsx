"use client"

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react"
import { jwtDecode } from "jwt-decode"

interface User {
  id: number
  email: string
  name: string
  cpf: string | null
  phone: string | null
  avatar: string | null
  direction_id: number | null
  direction_name: string | null
  management_id: number | null
  management_name: string | null
  coordination_id: number | null
  coordination_name: string | null
}

interface AuthContextType {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearAuth = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("user")
    document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
    document.cookie = "refresh_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT"
  }, [])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem("refresh_token")
    const access = localStorage.getItem("access_token")

    if (refresh && access) {
      try {
        await fetch("/api/v1/accounts/logout/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${access}`,
          },
          body: JSON.stringify({ refresh }),
        })
      } catch {
        // Silently fail - we're logging out anyway
      }
    }

    clearAuth()
    window.location.href = "/login"
  }, [clearAuth])

  const refreshAccessToken = useCallback(async (): Promise<boolean> => {
    const refresh = localStorage.getItem("refresh_token")
    if (!refresh) {
      clearAuth()
      return false
    }

    try {
      const response = await fetch("/api/v1/accounts/token/refresh/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      })

      if (!response.ok) {
        clearAuth()
        return false
      }

      const data = await response.json()

      setAccessToken(data.access)
      localStorage.setItem("access_token", data.access)
      document.cookie = `access_token=${data.access}; path=/`

      // simplejwt with rotate=True returns a new refresh token
      if (data.refresh) {
        localStorage.setItem("refresh_token", data.refresh)
        document.cookie = `refresh_token=${data.refresh}; path=/`
      }

      return true
    } catch {
      clearAuth()
      return false
    }
  }, [clearAuth])

  // Initialize from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem("access_token")
    const storedUser = localStorage.getItem("user")

    if (storedToken && storedUser) {
      try {
        const decoded = jwtDecode<{ exp: number }>(storedToken)
        const isExpired = decoded.exp * 1000 < Date.now()

        if (isExpired) {
          // Token expired, try refresh
          refreshAccessToken().then((success) => {
            if (success) {
              setUser(JSON.parse(storedUser))
            }
            setIsLoading(false)
          })
          return
        }

        setAccessToken(storedToken)
        setUser(JSON.parse(storedUser))
      } catch {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        localStorage.removeItem("user")
      }
    }
    setIsLoading(false)
  }, [refreshAccessToken])

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!accessToken) return

    const checkTokenExpiry = () => {
      try {
        const decoded = jwtDecode<{ exp: number }>(accessToken)
        const expiresIn = decoded.exp * 1000 - Date.now()

        if (expiresIn < 5 * 60 * 1000) {
          refreshAccessToken()
        }
      } catch {
        // Invalid token
      }
    }

    const interval = setInterval(checkTokenExpiry, 30000)
    return () => clearInterval(interval)
  }, [accessToken, refreshAccessToken])

  const login = async (email: string, password: string) => {
    const response = await fetch("/api/v1/accounts/token/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new Error(
        error?.detail || error?.non_field_errors?.[0] || "Email ou senha inválidos"
      )
    }

    const data = await response.json()

    setAccessToken(data.access)
    setUser(data.user)

    localStorage.setItem("access_token", data.access)
    localStorage.setItem("refresh_token", data.refresh)
    localStorage.setItem("user", JSON.stringify(data.user))

    document.cookie = `access_token=${data.access}; path=/`
    document.cookie = `refresh_token=${data.refresh}; path=/`
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: !!accessToken,
        isLoading,
        login,
        logout,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuthContext must be used within AuthProvider")
  }
  return context
}
