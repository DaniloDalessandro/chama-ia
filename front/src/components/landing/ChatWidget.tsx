"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  MessageCircle,
  X,
  Send,
  Bot,
  User,
  Minimize2,
  Loader2
} from "lucide-react"
import { atendimentoPublicService } from "@/services/atendimento-public.service"
import { useAtendimentoChat } from "@/hooks/useAtendimentoChat"
import type { MensagemAtendimento } from "@/types/atendimento"

const SESSION_STORAGE_KEY = "atendimento_session"

const quickActions = [
  "Como emitir uma nota fiscal?",
  "Problemas com certificado digital",
  "Duvidas sobre impostos",
  "Falar com atendente"
]

const GREETING_MESSAGE: MensagemAtendimento = {
  id: -1,
  atendimento: -1,
  remetente_tipo: "atendente",
  conteudo: "Ola! Sou a assistente virtual do ChamaNF. Posso te ajudar com a emissao de nota fiscal ou outra duvida?",
  criado_em: new Date().toISOString(),
}

interface AtendimentoSession {
  id: number
  token: string
}

interface ChatWidgetProps {
  isOpen: boolean
  onToggle: () => void
}

function loadStoredSession(): AtendimentoSession | null {
  if (typeof window === "undefined") return null
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AtendimentoSession) : null
  } catch {
    return null
  }
}

export function ChatWidget({ isOpen, onToggle }: ChatWidgetProps) {
  const [session, setSession] = useState<AtendimentoSession | null>(() => loadStoredSession())
  const [bootstrapMessages, setBootstrapMessages] = useState<MensagemAtendimento[]>([])
  const [inputValue, setInputValue] = useState("")
  const [preChatOpen, setPreChatOpen] = useState(false)
  const [pendingText, setPendingText] = useState("")
  const [nome, setNome] = useState("")
  const [email, setEmail] = useState("")
  const [creatingSession, setCreatingSession] = useState(false)
  const [analiseStatus, setAnaliseStatus] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { isConnected, messages: liveMessages, isTyping, sendMessage, sendTyping } = useAtendimentoChat({
    atendimentoId: session?.id ?? null,
    mode: "cliente",
    sessionToken: session?.token,
  })

  // Bootstrap do historico via REST -- o WS so entrega mensagens novas dai
  // em diante, nunca faz replay do que ja existia (inclui a mensagem_inicial
  // criada diretamente pelo POST /publico/, que nunca passa pelo WS).
  useEffect(() => {
    if (!session) return
    atendimentoPublicService
      .getMensagens(session.token)
      .then(setBootstrapMessages)
      .catch(() => {})
  }, [session])

  const allMessages = useMemo(() => {
    const map = new Map<number, MensagemAtendimento>()
    for (const m of bootstrapMessages) map.set(m.id, m)
    for (const m of liveMessages) map.set(m.id, m)
    const merged = Array.from(map.values()).sort((a, b) => a.criado_em.localeCompare(b.criado_em))
    return [GREETING_MESSAGE, ...merged]
  }, [bootstrapMessages, liveMessages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [allMessages])

  // Polling leve de analise_ia_status -- o evento WS "analise_status_changed"
  // nunca e disparado pelo backend nesta fase, entao o widget descobre o
  // resultado da analise via REST enquanto ainda estiver pendente/processando.
  useEffect(() => {
    if (!session) return

    let cancelled = false
    let interval: ReturnType<typeof setInterval> | null = null

    const poll = async () => {
      try {
        const status = await atendimentoPublicService.getStatus(session.token)
        if (cancelled) return
        setAnaliseStatus(status.analise_ia_status)
        if (status.analise_ia_status === "concluida" || status.analise_ia_status === "erro") {
          if (interval) clearInterval(interval)
        }
      } catch {
        // ignora falhas de polling -- nao e critico para a experiencia de chat
      }
    }

    poll()
    interval = setInterval(poll, 4000)

    return () => {
      cancelled = true
      if (interval) clearInterval(interval)
    }
  }, [session])

  const persistSession = (next: AtendimentoSession) => {
    setSession(next)
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(next))
    } catch {
      // sessionStorage indisponivel (modo privado etc.) -- degrada graciosamente
    }
  }

  const handleSend = async () => {
    if (!inputValue.trim()) return

    if (!session) {
      setPendingText(inputValue)
      setInputValue("")
      setPreChatOpen(true)
      return
    }

    sendMessage(inputValue)
    setInputValue("")
  }

  const handleCreateSession = async () => {
    if (!nome.trim() || !email.trim()) return

    setCreatingSession(true)
    try {
      const response = await atendimentoPublicService.criar({
        nome,
        email,
        mensagem_inicial: pendingText || undefined,
      })
      persistSession({ id: response.id, token: response.session_token })
      setPreChatOpen(false)
      setPendingText("")
    } catch {
      // erro de rede/validacao -- mantem o formulario aberto para nova tentativa
    } finally {
      setCreatingSession(false)
    }
  }

  const handleQuickAction = (action: string) => {
    setInputValue(action)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInputChange = (value: string) => {
    setInputValue(value)
    sendTyping()
  }

  const showAnalisando = session !== null && (analiseStatus === "pendente" || analiseStatus === "processando")

  return (
    <>
      {/* Chat Button */}
      <button
        onClick={onToggle}
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-all duration-300 hover:scale-110 hover:shadow-xl ${
          isOpen ? "scale-0 opacity-0" : "scale-100 opacity-100"
        }`}
        aria-label="Abrir chat"
      >
        <MessageCircle className="h-6 w-6" />
      </button>

      {/* Chat Window */}
      <div
        className={`fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border bg-background shadow-2xl transition-all duration-300 ${
          isOpen
            ? "scale-100 opacity-100"
            : "pointer-events-none scale-95 opacity-0"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between bg-primary px-4 py-3 text-primary-foreground">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/20">
                <Bot className="h-6 w-6" />
              </div>
              <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-primary bg-green-400" />
            </div>
            <div>
              <h3 className="font-semibold">Atendimento ChamaNF</h3>
              <p className="text-xs text-primary-foreground/80">
                {showAnalisando ? "Analisando sua mensagem..." : "Online agora"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-primary-foreground hover:bg-white/20"
              onClick={onToggle}
            >
              <Minimize2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-primary-foreground hover:bg-white/20"
              onClick={onToggle}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {allMessages.map((message) => {
            if (message.remetente_tipo === "sistema") {
              return (
                <div key={message.id} className="flex justify-center">
                  <p className="rounded-full bg-muted px-3 py-1 text-xs italic text-muted-foreground">
                    {message.conteudo}
                  </p>
                </div>
              )
            }

            const isCliente = message.remetente_tipo === "cliente"

            return (
              <div
                key={message.id}
                className={`flex ${isCliente ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`flex max-w-[85%] gap-2 ${
                    isCliente ? "flex-row-reverse" : "flex-row"
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${
                      isCliente
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {isCliente ? (
                      <User className="h-4 w-4" />
                    ) : (
                      <Bot className="h-4 w-4" />
                    )}
                  </div>
                  <div
                    className={`rounded-2xl px-4 py-2 ${
                      isCliente
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm">{message.conteudo}</p>
                    <p
                      className={`mt-1 text-xs ${
                        isCliente
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground"
                      }`}
                    >
                      {new Date(message.criado_em).toLocaleTimeString("pt-BR", {
                        hour: "2-digit",
                        minute: "2-digit"
                      })}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}

          {isTyping.atendente && (
            <div className="flex justify-start">
              <div className="flex max-w-[85%] gap-2">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-muted">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-2xl bg-muted px-4 py-3">
                  <div className="flex gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.3s]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50 [animation-delay:-0.15s]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/50" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Actions */}
        {allMessages.length <= 2 && !preChatOpen && (
          <div className="border-t px-4 py-2">
            <p className="mb-2 text-xs text-muted-foreground">Perguntas frequentes:</p>
            <div className="flex flex-wrap gap-2">
              {quickActions.map((action, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickAction(action)}
                  className="rounded-full border bg-background px-3 py-1 text-xs transition-colors hover:bg-muted"
                >
                  {action}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Pre-chat form (nome/email) -- exibido antes da primeira mensagem real */}
        {preChatOpen ? (
          <div className="border-t p-4 space-y-2">
            <p className="text-xs text-muted-foreground">
              Para iniciar o atendimento, informe seu nome e e-mail:
            </p>
            <Input
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              placeholder="Seu nome"
              disabled={creatingSession}
            />
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              disabled={creatingSession}
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setPreChatOpen(false)}
                disabled={creatingSession}
              >
                Cancelar
              </Button>
              <Button
                className="flex-1"
                onClick={handleCreateSession}
                disabled={!nome.trim() || !email.trim() || creatingSession}
              >
                {creatingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : "Iniciar"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Input
                value={inputValue}
                onChange={(e) => handleInputChange(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua mensagem..."
                className="flex-1"
              />
              <Button
                onClick={handleSend}
                disabled={!inputValue.trim()}
                size="icon"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              {session && !isConnected ? "Reconectando..." : "Atendimento via IA ou humano disponivel"}
            </p>
          </div>
        )}
      </div>
    </>
  )
}
