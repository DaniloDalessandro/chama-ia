/**
 * Servico para configuracao do email que recebe chamados (ingestao via IMAP)
 */
import { apiClient } from "@/lib/api/client"

export interface EmailConfig {
  configured: boolean
  id?: number
  email?: string
  imap_host?: string
  imap_port?: number
  use_ssl?: boolean
  folder?: string
  is_active?: boolean
  last_checked_at?: string | null
  last_error?: string
  total_processed?: number
  updated_at?: string
}

export interface EmailConfigInput {
  email: string
  password?: string
  imap_host: string
  imap_port: number
  use_ssl: boolean
  folder: string
  is_active: boolean
}

export interface CheckNowResult {
  enabled: boolean
  processados: number
  erros: number
  erro_msg?: string
}

export const emailConfigService = {
  get(): Promise<EmailConfig> {
    return apiClient.get<EmailConfig>("/chamados/email-config/")
  },

  save(data: EmailConfigInput): Promise<EmailConfig> {
    return apiClient.put<EmailConfig>("/chamados/email-config/", data)
  },

  checkNow(): Promise<CheckNowResult> {
    return apiClient.post<CheckNowResult>("/chamados/email-config/verificar-agora/")
  },
}
