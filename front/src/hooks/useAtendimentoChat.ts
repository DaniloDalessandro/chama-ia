"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import type { AtendimentoWsEnvelope, MensagemAtendimento } from "@/types/atendimento"

const WS_RECONNECT_DELAYS = [1000, 2000, 5000, 10000, 30000]
const WS_MAX_RECONNECT_DELAY = 60000
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
const WS_BASE_URL = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")

const TYPING_TIMEOUT_MS = 3000
const TYPING_THROTTLE_MS = 2000

export interface UseAtendimentoChatOptions {
  atendimentoId: number | null
  mode: "cliente" | "staff"
  sessionToken?: string
  initialMessages?: MensagemAtendimento[]
}

export interface UseAtendimentoChatResult {
  isConnected: boolean
  messages: MensagemAtendimento[]
  isTyping: { cliente: boolean; atendente: boolean }
  atendimentoStatus: {
    status_atendimento: string
    analise_ia_status: string
    prioridade: string
  } | null
  participants: { atendente: { id: number; name: string } | null }
  sendMessage: (conteudo: string) => void
  sendTyping: () => void
}

function getAccessTokenFromCookie(): string | null {
  return (
    document.cookie
      .split("; ")
      .find((row) => row.startsWith("access_token="))
      ?.split("=")[1] || null
  )
}

export function useAtendimentoChat({
  atendimentoId,
  mode,
  sessionToken,
  initialMessages,
}: UseAtendimentoChatOptions): UseAtendimentoChatResult {
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<MensagemAtendimento[]>(() => initialMessages ?? [])
  const [isTyping, setIsTyping] = useState({ cliente: false, atendente: false })
  const [atendimentoStatus, setAtendimentoStatus] =
    useState<UseAtendimentoChatResult["atendimentoStatus"]>(null)
  const [participants, setParticipants] = useState<UseAtendimentoChatResult["participants"]>({
    atendente: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const reconnectAttemptsRef = useRef(0)
  const isManuallyClosedRef = useRef(false)
  const typingTimeoutsRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const lastTypingSentRef = useRef(0)

  const connectWebSocket = useCallback(() => {
    if (isManuallyClosedRef.current || atendimentoId === null) return

    const token = mode === "cliente" ? sessionToken : getAccessTokenFromCookie()
    if (!token) {
      console.warn("useAtendimentoChat: nenhum token disponível, conexão WS não iniciada")
      return
    }

    const wsUrl = `${WS_BASE_URL}/ws/atendimento/${atendimentoId}/?token=${token}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        let data: AtendimentoWsEnvelope
        try {
          data = JSON.parse(event.data)
        } catch {
          return
        }

        if (data.type === "connection_established") {
          setAtendimentoStatus(data.atendimento)
        } else if (data.type === "chat_message") {
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.mensagem.id)) return prev
            return [...prev, data.mensagem]
          })
        } else if (data.type === "typing") {
          const role = data.remetente_tipo
          setIsTyping((prev) => ({ ...prev, [role]: true }))
          if (typingTimeoutsRef.current[role]) {
            clearTimeout(typingTimeoutsRef.current[role])
          }
          typingTimeoutsRef.current[role] = setTimeout(() => {
            setIsTyping((prev) => ({ ...prev, [role]: false }))
          }, TYPING_TIMEOUT_MS)
        } else if (data.type === "staff_joined") {
          setParticipants({ atendente: data.atendente })
        } else if (data.type === "staff_left") {
          setParticipants({ atendente: null })
        } else if (data.type === "analise_status_changed") {
          setAtendimentoStatus((prev) => ({
            status_atendimento: prev?.status_atendimento ?? "",
            analise_ia_status: data.analise_ia_status ?? prev?.analise_ia_status ?? "",
            prioridade: data.prioridade ?? prev?.prioridade ?? "",
          }))
        } else if (data.type === "error") {
          toast.error(data.message)
        }
      }

      ws.onerror = () => {
        setIsConnected(false)
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null

        if (!isManuallyClosedRef.current) {
          const delay = Math.min(
            WS_RECONNECT_DELAYS[reconnectAttemptsRef.current] || WS_MAX_RECONNECT_DELAY,
            WS_MAX_RECONNECT_DELAY
          )
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1
            connectWebSocket()
          }, delay)
        }
      }
    } catch (error) {
      console.error("useAtendimentoChat: erro ao conectar WebSocket", error)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atendimentoId, mode, sessionToken])

  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "ping", timestamp: new Date().toISOString() }))
      }
    }, 30000)

    return () => clearInterval(pingInterval)
  }, [])

  useEffect(() => {
    if (atendimentoId === null) return

    isManuallyClosedRef.current = false
    connectWebSocket()

    return () => {
      isManuallyClosedRef.current = true

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      Object.values(typingTimeoutsRef.current).forEach(clearTimeout)

      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atendimentoId, connectWebSocket])

  const sendMessage = useCallback(
    (conteudo: string) => {
      if (!conteudo.trim() || atendimentoId === null) return

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "send_message", conteudo }))
        return
      }

      // Fallback REST só existe para o lado staff -- clientes anônimos não
      // têm um endpoint público de envio, apenas o WS.
      if (mode === "staff") {
        atendimentoAdminService
          .sendMensagem(atendimentoId, conteudo)
          .then((mensagem) => {
            setMessages((prev) => (prev.some((m) => m.id === mensagem.id) ? prev : [...prev, mensagem]))
          })
          .catch(() => toast.error("Erro ao enviar mensagem"))
      } else {
        toast.error("Reconectando... tente novamente em instantes")
      }
    },
    [atendimentoId, mode]
  )

  const sendTyping = useCallback(() => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    const now = Date.now()
    if (now - lastTypingSentRef.current < TYPING_THROTTLE_MS) return
    lastTypingSentRef.current = now
    wsRef.current.send(JSON.stringify({ action: "typing" }))
  }, [])

  return {
    isConnected,
    messages,
    isTyping,
    atendimentoStatus,
    participants,
    sendMessage,
    sendTyping,
  }
}
