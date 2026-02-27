/**
 * Utilitários para gerenciamento seguro de cookies
 */

interface CookieOptions {
  path?: string
  maxAge?: number
  expires?: Date
  domain?: string
  secure?: boolean
  sameSite?: 'strict' | 'lax' | 'none'
}

/**
 * Define um cookie de forma segura com flags de segurança apropriadas
 *
 * NOTA IMPORTANTE: HttpOnly não pode ser setado via JavaScript!
 * Para cookies HttpOnly, o backend deve setar via Set-Cookie header.
 * Esta função adiciona as outras flags de segurança disponíveis.
 */
export function setSecureCookie(
  name: string,
  value: string,
  options: CookieOptions = {}
): void {
  const {
    path = '/',
    maxAge,
    expires,
    domain,
    secure = window.location.protocol === 'https:',
    sameSite = 'lax'
  } = options

  let cookieString = `${name}=${encodeURIComponent(value)}`

  cookieString += `; path=${path}`

  if (maxAge) {
    cookieString += `; max-age=${maxAge}`
  }

  if (expires) {
    cookieString += `; expires=${expires.toUTCString()}`
  }

  if (domain) {
    cookieString += `; domain=${domain}`
  }

  // Secure flag: cookie só enviado via HTTPS
  if (secure) {
    cookieString += '; Secure'
  }

  // SameSite: proteção contra CSRF
  if (sameSite) {
    cookieString += `; SameSite=${sameSite}`
  }

  document.cookie = cookieString
}

/**
 * Remove um cookie de forma segura
 */
export function deleteCookie(name: string, path: string = '/'): void {
  // Para deletar, setamos uma data no passado
  const expires = new Date(0).toUTCString()
  document.cookie = `${name}=; path=${path}; expires=${expires}; SameSite=Lax`
}

/**
 * Lê um cookie
 */
export function getCookie(name: string): string | null {
  const nameEQ = name + '='
  const cookies = document.cookie.split(';')

  for (let cookie of cookies) {
    cookie = cookie.trim()
    if (cookie.indexOf(nameEQ) === 0) {
      return decodeURIComponent(cookie.substring(nameEQ.length))
    }
  }

  return null
}

/**
 * Define os tokens de autenticação com segurança máxima
 *
 * ATENÇÃO: Idealmente, tokens deveriam ser HttpOnly e setados pelo backend.
 * Como estamos setando via JavaScript, usamos todas as outras proteções disponíveis.
 */
export function setAuthTokens(accessToken: string, refreshToken?: string): void {
  const isProduction = process.env.NODE_ENV === 'production'

  // Access token (15 minutos)
  setSecureCookie('access_token', accessToken, {
    path: '/',
    maxAge: 15 * 60, // 15 minutos
    secure: isProduction, // Apenas HTTPS em produção
    sameSite: 'strict' // Máxima proteção contra CSRF
  })

  // Refresh token (7 dias)
  if (refreshToken) {
    setSecureCookie('refresh_token', refreshToken, {
      path: '/',
      maxAge: 7 * 24 * 60 * 60, // 7 dias
      secure: isProduction,
      sameSite: 'strict'
    })
  }
}

/**
 * Remove os tokens de autenticação
 */
export function clearAuthTokens(): void {
  deleteCookie('access_token')
  deleteCookie('refresh_token')
}
