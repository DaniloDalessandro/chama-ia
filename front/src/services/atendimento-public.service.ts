/**
 * Serviço público (anônimo) de Atendimento -- usado pelo widget de chat.
 * `session_token` é a única credencial do cliente anônimo, nunca o JWT.
 * Endpoints mantêm a barra final exatamente como o backend expõe.
 */
import { apiClient } from "@/lib/api/client"
import type {
  AtendimentoPublicoCreateResponse,
  AtendimentoPublicoStatus,
  MensagemAtendimento,
} from "@/types/atendimento"

export interface AtendimentoPublicoCreateInput {
  nome: string
  email: string
  telefone?: string
  mensagem_inicial?: string
}

export const atendimentoPublicService = {
  async criar(payload: AtendimentoPublicoCreateInput): Promise<AtendimentoPublicoCreateResponse> {
    return apiClient.post<AtendimentoPublicoCreateResponse>("/atendimento/publico/", payload, {
      skipAuth: true,
    })
  },

  async getStatus(sessionToken: string): Promise<AtendimentoPublicoStatus> {
    return apiClient.get<AtendimentoPublicoStatus>(`/atendimento/publico/${sessionToken}/`, {
      skipAuth: true,
    })
  },

  async getMensagens(sessionToken: string): Promise<MensagemAtendimento[]> {
    return apiClient.get<MensagemAtendimento[]>(`/atendimento/publico/${sessionToken}/mensagens/`, {
      skipAuth: true,
    })
  },
}
