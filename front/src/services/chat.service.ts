export interface ChatMessage {
  id: string
  content: string
  sender: "user" | "bot" | "agent"
  timestamp: Date
}

export interface ChatSession {
  id: string
  messages: ChatMessage[]
  status: "active" | "closed"
  createdAt: Date
}

// Tipo para conexao WebSocket futura
export type ChatEventType = "message" | "typing" | "agent_joined" | "session_closed"

export interface ChatEvent {
  type: ChatEventType
  payload: unknown
}

export class ChatService {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private messageHandlers: ((message: ChatMessage) => void)[] = []
  private typingHandlers: ((isTyping: boolean) => void)[] = []

  // Conectar ao WebSocket (implementacao futura)
  async connect(sessionId?: string): Promise<string> {
    // Simular criacao de sessao
    this.sessionId = sessionId || this.generateSessionId()

    // TODO: Implementar conexao WebSocket real
    // this.ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/chat/${this.sessionId}`)

    return this.sessionId
  }

  // Desconectar
  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.sessionId = null
  }

  // Enviar mensagem
  async sendMessage(content: string): Promise<ChatMessage> {
    const message: ChatMessage = {
      id: this.generateMessageId(),
      content,
      sender: "user",
      timestamp: new Date()
    }

    // TODO: Enviar via WebSocket
    // this.ws?.send(JSON.stringify({ type: "message", payload: message }))

    return message
  }

  // Registrar handler de mensagens
  onMessage(handler: (message: ChatMessage) => void): () => void {
    this.messageHandlers.push(handler)
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler)
    }
  }

  // Registrar handler de typing
  onTyping(handler: (isTyping: boolean) => void): () => void {
    this.typingHandlers.push(handler)
    return () => {
      this.typingHandlers = this.typingHandlers.filter(h => h !== handler)
    }
  }

  // Obter historico de mensagens
  async getHistory(sessionId: string): Promise<ChatMessage[]> {
    // TODO: Implementar chamada API
    return []
  }

  // Solicitar atendente humano
  async requestHumanAgent(): Promise<void> {
    // TODO: Implementar via WebSocket
    // this.ws?.send(JSON.stringify({ type: "request_agent" }))
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }
}

// Singleton para uso global
export const chatService = new ChatService()
