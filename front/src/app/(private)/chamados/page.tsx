"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from "@dnd-kit/core"
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable"
import { Loader2, Search, RefreshCw, Filter, UserCircle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/components/ui/sonner"
import { KanbanColumn } from "@/components/chamados/KanbanColumn"
import { KanbanCard } from "@/components/chamados/KanbanCard"
import { KanbanSkeleton } from "@/components/common/LoadingSkeletons"
import { chamadoAdminService, type Chamado } from "@/services/chamado-admin.service"

type StatusKanban = "novo" | "em_andamento" | "concluido"

const columns: { id: StatusKanban; title: string; color: string }[] = [
  { id: "novo", title: "Chamados Novos", color: "bg-blue-500" },
  { id: "em_andamento", title: "Sendo Tratados", color: "bg-yellow-500" },
  { id: "concluido", title: "Concluidos", color: "bg-green-500" },
]

export default function ChamadosPage() {
  const router = useRouter()
  const [chamados, setChamados] = useState<Chamado[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [filterTipo, setFilterTipo] = useState<string>("")
  const [filterPrioridade, setFilterPrioridade] = useState<string>("")
  const [filterAtendente, setFilterAtendente] = useState<string>("")
  const [atendentes, setAtendentes] = useState<{ id: number; name: string }[]>([])
  const [activeCard, setActiveCard] = useState<Chamado | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const fetchChamados = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await chamadoAdminService.list({
        search: searchTerm || undefined,
        tipo: filterTipo || undefined,
        prioridade: filterPrioridade || undefined,
        atendente: filterAtendente || undefined,
        ordering: "-created_at",
      })
      setChamados(data || [])
    } catch (err) {
      console.error("Erro ao carregar chamados:", err)
      setChamados([])
    } finally {
      setIsLoading(false)
      setIsInitialLoading(false)
    }
  }, [searchTerm, filterTipo, filterPrioridade, filterAtendente])

  useEffect(() => {
    fetchChamados()
  }, [fetchChamados])

  useEffect(() => {
    chamadoAdminService.listAtendentes().then(setAtendentes)
  }, [])

  const getChamadosByStatus = (status: StatusKanban) => {
    return chamados.filter((c) => c.status_kanban === status)
  }

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const chamado = chamados.find((c) => c.id === active.id)
    if (chamado) {
      setActiveCard(chamado)
    }
  }

  const handleDragOver = (event: DragOverEvent) => {
    // Podemos adicionar logica de preview aqui se necessario
  }

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event
    setActiveCard(null)

    if (!over) return

    const chamadoId = active.id as number
    const newStatus = over.id as StatusKanban

    // Encontrar o chamado atual
    const chamado = chamados.find((c) => c.id === chamadoId)
    if (!chamado) return

    // Se o status nao mudou, nao faz nada
    if (chamado.status_kanban === newStatus) return

    // Atualizar otimisticamente
    const oldStatus = chamado.status_kanban
    setChamados((prev) =>
      prev.map((c) =>
        c.id === chamadoId ? { ...c, status_kanban: newStatus } : c
      )
    )

    try {
      const response = await chamadoAdminService.updateStatusKanban(chamadoId, newStatus)
      if (response.success) {
        toast.success("Status atualizado com sucesso!")
      } else {
        // Reverter se falhar
        setChamados((prev) =>
          prev.map((c) =>
            c.id === chamadoId ? { ...c, status_kanban: oldStatus } : c
          )
        )
        toast.error(response.message || "Erro ao atualizar status")
      }
    } catch (err) {
      // Reverter se falhar
      setChamados((prev) =>
        prev.map((c) =>
          c.id === chamadoId ? { ...c, status_kanban: oldStatus } : c
        )
      )
      toast.error("Erro ao atualizar status")
    }
  }

  const handleCardClick = (chamado: Chamado) => {
    window.open(`/chamados/${chamado.id}`, "_blank", "noopener,noreferrer")
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchChamados()
  }

  const clearFilters = () => {
    setSearchTerm("")
    setFilterTipo("")
    setFilterPrioridade("")
    setFilterAtendente("")
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chamados</h1>
          <p className="text-muted-foreground">
            Gerencie os chamados arrastando entre as colunas
          </p>
        </div>
        <Button onClick={fetchChamados} variant="outline" size="sm">
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por protocolo, nome, email, assunto..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </form>

        <div className="flex gap-2">
          <Select value={filterTipo} onValueChange={setFilterTipo}>
            <SelectTrigger className="w-[160px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos os tipos</SelectItem>
              <SelectItem value="nota-fiscal">Nota Fiscal</SelectItem>
              <SelectItem value="erro-sistema">Erro no Sistema</SelectItem>
              <SelectItem value="financeiro">Financeiro</SelectItem>
              <SelectItem value="outros">Outros</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterPrioridade} onValueChange={setFilterPrioridade}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Prioridade" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todas</SelectItem>
              <SelectItem value="baixa">Baixa</SelectItem>
              <SelectItem value="media">Media</SelectItem>
              <SelectItem value="alta">Alta</SelectItem>
              <SelectItem value="urgente">Urgente</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterAtendente} onValueChange={setFilterAtendente}>
            <SelectTrigger className="w-[180px]">
              <UserCircle className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Atendente" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos</SelectItem>
              <SelectItem value="null">Sem atendente</SelectItem>
              {atendentes.map((a) => (
                <SelectItem key={a.id} value={String(a.id)}>
                  {a.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {(searchTerm || filterTipo || filterPrioridade || filterAtendente) && (
            <Button variant="ghost" size="sm" onClick={clearFilters}>
              Limpar
            </Button>
          )}
        </div>
      </div>

      {/* Kanban Board */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="relative">
          {isInitialLoading ? (
            <KanbanSkeleton columns={3} />
          ) : (
            <>
              {/* Loading overlay (apenas para refresh) */}
              {isLoading && (
                <div className="absolute inset-0 bg-background/50 flex items-center justify-center z-10 rounded-xl">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[calc(100vh-220px)]">
                {columns.map((column) => (
                  <KanbanColumn
                    key={column.id}
                    id={column.id}
                    title={column.title}
                    color={column.color}
                    chamados={getChamadosByStatus(column.id)}
                    onCardClick={handleCardClick}
                  />
                ))}
              </div>
            </>
          )}
        </div>

        <DragOverlay>
          {activeCard && (
            <KanbanCard chamado={activeCard} isDragging />
          )}
        </DragOverlay>
      </DndContext>
    </div>
  )
}
