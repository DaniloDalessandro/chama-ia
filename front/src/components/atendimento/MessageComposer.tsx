"use client"

import { useState } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface MessageComposerProps {
  isConnected: boolean
  onSend: (conteudo: string) => void
  onTyping: () => void
}

export function MessageComposer({ isConnected, onSend, onTyping }: MessageComposerProps) {
  const [value, setValue] = useState("")

  const handleSend = () => {
    if (!value.trim()) return
    onSend(value)
    setValue("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="space-y-2 border-t pt-3">
      {!isConnected && (
        <p className="text-xs text-amber-600 dark:text-amber-400">Reconectando...</p>
      )}
      <div className="flex gap-2">
        <Textarea
          value={value}
          onChange={(e) => {
            setValue(e.target.value)
            onTyping()
          }}
          onKeyDown={handleKeyDown}
          placeholder="Digite sua mensagem... (Enter envia, Shift+Enter quebra linha)"
          rows={2}
          className="flex-1 resize-none"
        />
        <Button onClick={handleSend} disabled={!value.trim()} size="icon" className="h-auto">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
