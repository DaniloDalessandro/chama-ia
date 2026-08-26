import { Globe } from "lucide-react"
import { cn } from "@/lib/utils"
import type { MensagemAtendimento } from "@/types/atendimento"

function formatHora(dateString: string) {
  return new Date(dateString).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
}

interface ConversaThreadProps {
  mensagens: MensagemAtendimento[]
}

/**
 * 3 variantes visuais (cliente/atendente/sistema) -- uma a mais que o
 * padrão de 2 variantes usado no thread de comentários de Chamados.
 */
export function ConversaThread({ mensagens }: ConversaThreadProps) {
  if (mensagens.length === 0) {
    return <p className="py-4 text-center text-sm text-muted-foreground">Nenhuma mensagem ainda.</p>
  }

  return (
    <div className="space-y-3">
      {mensagens.map((mensagem) => {
        if (mensagem.remetente_tipo === "sistema") {
          return (
            <div key={mensagem.id} className="flex justify-center">
              <p className="rounded-full bg-muted px-3 py-1 text-xs italic text-muted-foreground">
                {mensagem.conteudo}
              </p>
            </div>
          )
        }

        const isCliente = mensagem.remetente_tipo === "cliente"

        return (
          <div
            key={mensagem.id}
            className={cn(
              "rounded-lg p-3",
              isCliente ? "bg-blue-50 dark:bg-blue-950/50 ml-8" : "bg-muted mr-8"
            )}
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1 text-xs font-medium">
                {isCliente ? "Cliente" : (
                  <>
                    <Globe className="h-3 w-3" />
                    Atendente
                  </>
                )}
              </span>
              <span className="text-xs text-muted-foreground">{formatHora(mensagem.criado_em)}</span>
            </div>
            <p className="whitespace-pre-wrap text-sm">{mensagem.conteudo}</p>
          </div>
        )
      })}
    </div>
  )
}
