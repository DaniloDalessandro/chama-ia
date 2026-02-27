"use client"

import { useDroppable } from "@dnd-kit/core"
import { cn } from "@/lib/utils"
import { KanbanCard } from "./KanbanCard"
import type { Chamado } from "@/services/chamado-admin.service"

interface KanbanColumnProps {
  id: string
  title: string
  color: string
  chamados: Chamado[]
  onCardClick: (chamado: Chamado) => void
}

export function KanbanColumn({
  id,
  title,
  color,
  chamados,
  onCardClick,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id,
  })

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex flex-col rounded-xl border bg-card transition-colors h-full",
        isOver && "ring-2 ring-primary ring-offset-2"
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <div className={cn("h-3 w-3 rounded-full", color)} />
        <h3 className="font-semibold">{title}</h3>
        <span className="ml-auto rounded-full bg-muted px-2.5 py-0.5 text-sm font-medium">
          {chamados.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chamados.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            Nenhum chamado
          </div>
        ) : (
          chamados.map((chamado) => (
            <KanbanCard
              key={chamado.id}
              chamado={chamado}
              onClick={() => onCardClick(chamado)}
            />
          ))
        )}
      </div>
    </div>
  )
}
