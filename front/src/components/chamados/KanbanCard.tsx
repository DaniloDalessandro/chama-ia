"use client"

import { useRef } from "react"
import { useDraggable } from "@dnd-kit/core"
import { CSS } from "@dnd-kit/utilities"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  FileText,
  AlertCircle,
  DollarSign,
  HelpCircle,
  Clock,
  User,
  Paperclip,
  MessageSquare,
  Brain,
  RefreshCcw,
} from "lucide-react"
import type { Chamado } from "@/services/chamado-admin.service"

interface KanbanCardProps {
  chamado: Chamado
  onClick?: () => void
  isDragging?: boolean
}

const tipoIcons: Record<string, typeof FileText> = {
  "nota-fiscal": FileText,
  "erro-sistema": AlertCircle,
  financeiro: DollarSign,
  outros: HelpCircle,
}

const prioridadeColors: Record<string, string> = {
  baixa: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  media: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  alta: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  urgente: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
}

function formatDate(dateString: string) {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  if (hours < 1) return "Agora"
  if (hours < 24) return `${hours}h atras`
  if (days < 7) return `${days}d atras`
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })
}

export function KanbanCard({ chamado, onClick, isDragging }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: chamado.id,
  })
  const pointerStartRef = useRef<{ x: number; y: number } | null>(null)

  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
      }
    : undefined

  const TipoIcon = tipoIcons[chamado.tipo] || HelpCircle

  // dnd-kit's PointerSensor calls preventDefault() on pointerdown,
  // which blocks the browser from generating a click event.
  // We work around this by tracking pointer position and detecting
  // clicks manually via onPointerUp.
  const { onPointerDown: dndPointerDown, ...restListeners } = listeners || {}

  const handlePointerDown = (e: React.PointerEvent) => {
    pointerStartRef.current = { x: e.clientX, y: e.clientY }
    if (dndPointerDown) {
      dndPointerDown(e as any)
    }
  }

  const handlePointerUp = (e: React.PointerEvent) => {
    if (pointerStartRef.current) {
      const dx = e.clientX - pointerStartRef.current.x
      const dy = e.clientY - pointerStartRef.current.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < 8) {
        onClick?.()
      }
    }
    pointerStartRef.current = null
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      {...restListeners}
      {...attributes}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      className={cn(
        "cursor-grab select-none transition-all hover:shadow-md active:cursor-grabbing",
        isDragging && "shadow-xl rotate-3 opacity-90",
        chamado.prioridade === "urgente" && "border-l-4 border-l-red-500"
      )}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header com protocolo e tipo */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TipoIcon className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">
              #{chamado.protocolo}
            </span>
            {/* Indicadores IA */}
            {chamado.ia_processed && (
              <Brain className="h-3 w-3 text-purple-500" title="Processado por IA" />
            )}
            {chamado.is_recorrente && (
              <RefreshCcw className="h-3 w-3 text-yellow-500" title="Chamado recorrente detectado" />
            )}
          </div>
          <Badge
            variant="secondary"
            className={cn("text-xs", prioridadeColors[chamado.prioridade])}
          >
            {chamado.prioridade_display}
          </Badge>
        </div>

        {/* Assunto */}
        <h4 className="font-medium leading-tight line-clamp-2">
          {chamado.assunto}
        </h4>

        {/* Tipo badge */}
        <Badge variant="outline" className="text-xs">
          {chamado.tipo_display}
        </Badge>

        {/* Footer com info adicional */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
          <div className="flex items-center gap-3">
            {/* Nome do solicitante */}
            <div className="flex items-center gap-1">
              <User className="h-3 w-3" />
              <span className="truncate max-w-[80px]">{chamado.nome}</span>
            </div>

            {/* Anexos */}
            {chamado.total_anexos > 0 && (
              <div className="flex items-center gap-1">
                <Paperclip className="h-3 w-3" />
                <span>{chamado.total_anexos}</span>
              </div>
            )}

            {/* Comentarios */}
            {chamado.total_comentarios > 0 && (
              <div className="flex items-center gap-1">
                <MessageSquare className="h-3 w-3" />
                <span>{chamado.total_comentarios}</span>
              </div>
            )}
          </div>

          {/* Data */}
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formatDate(chamado.created_at)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
