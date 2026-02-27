"use client"

import { useState, useRef, useEffect } from "react"
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

interface Message {
  id: string
  content: string
  sender: "user" | "bot" | "agent"
  timestamp: Date
}

const quickActions = [
  "Como emitir uma nota fiscal?",
  "Problemas com certificado digital",
  "Duvidas sobre impostos",
  "Falar com atendente"
]

const initialMessages: Message[] = [
  {
    id: "1",
    content: "Ola! Sou a Alice, assistente virtual do ChamaNF. Posso te ajudar com a emissao de nota fiscal ou outra duvida?",
    sender: "bot",
    timestamp: new Date()
  }
]

interface ChatWidgetProps {
  isOpen: boolean
  onToggle: () => void
}

export function ChatWidget({ isOpen, onToggle }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [inputValue, setInputValue] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const generateBotResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase()

    if (lowerMessage.includes("emitir") || lowerMessage.includes("emissao") || lowerMessage.includes("nota")) {
      return "Para emitir uma nota fiscal, acesse o menu 'Notas Fiscais' > 'Nova Nota'. Preencha os dados do cliente, produtos/servicos e clique em 'Emitir'. A nota sera processada automaticamente pela SEFAZ. Posso ajudar com mais alguma coisa?"
    }
    if (lowerMessage.includes("certificado")) {
      return "O certificado digital A1 ou A3 e necessario para emissao de NF-e. Verifique se esta instalado corretamente e dentro da validade. Caso tenha problemas, acesse Configuracoes > Certificado Digital para reimportar. Precisa de mais ajuda?"
    }
    if (lowerMessage.includes("imposto") || lowerMessage.includes("tributo")) {
      return "Os impostos sao calculados automaticamente com base no NCM do produto e CFOP da operacao. Voce pode configurar aliquotas especificas em Configuracoes > Tributacao. Quer saber mais sobre algum imposto especifico?"
    }
    if (lowerMessage.includes("atendente") || lowerMessage.includes("humano")) {
      return "Vou transferir voce para um de nossos atendentes. Aguarde um momento... Em horario comercial, o tempo medio de espera e de 2 minutos."
    }
    if (lowerMessage.includes("cancelar")) {
      return "Para cancelar uma nota fiscal, acesse 'Notas Fiscais' > 'Emitidas', localize a nota desejada e clique em 'Cancelar'. Lembre-se que o cancelamento so e possivel em ate 24 horas apos a emissao. Posso ajudar com mais alguma coisa?"
    }

    return "Entendi sua duvida! Para um atendimento mais preciso, recomendo abrir um chamado com detalhes da sua solicitacao, ou se preferir, posso transferir para um atendente. O que prefere?"
  }

  const handleSend = async () => {
    if (!inputValue.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      sender: "user",
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue("")
    setIsTyping(true)

    // Simular delay de resposta
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000))

    const botResponse: Message = {
      id: (Date.now() + 1).toString(),
      content: generateBotResponse(inputValue),
      sender: "bot",
      timestamp: new Date()
    }

    setIsTyping(false)
    setMessages(prev => [...prev, botResponse])
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
        {/* Notification badge */}
        <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
          1
        </span>
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
              <p className="text-xs text-primary-foreground/80">Online agora</p>
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
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.sender === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`flex max-w-[85%] gap-2 ${
                  message.sender === "user" ? "flex-row-reverse" : "flex-row"
                }`}
              >
                <div
                  className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full ${
                    message.sender === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  {message.sender === "user" ? (
                    <User className="h-4 w-4" />
                  ) : (
                    <Bot className="h-4 w-4" />
                  )}
                </div>
                <div
                  className={`rounded-2xl px-4 py-2 ${
                    message.sender === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="text-sm">{message.content}</p>
                  <p
                    className={`mt-1 text-xs ${
                      message.sender === "user"
                        ? "text-primary-foreground/70"
                        : "text-muted-foreground"
                    }`}
                  >
                    {message.timestamp.toLocaleTimeString("pt-BR", {
                      hour: "2-digit",
                      minute: "2-digit"
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {isTyping && (
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
        {messages.length <= 2 && (
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

        {/* Input */}
        <div className="border-t p-4">
          <div className="flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Digite sua mensagem..."
              className="flex-1"
              disabled={isTyping}
            />
            <Button
              onClick={handleSend}
              disabled={!inputValue.trim() || isTyping}
              size="icon"
            >
              {isTyping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Atendimento via IA ou humano disponivel
          </p>
        </div>
      </div>
    </>
  )
}
