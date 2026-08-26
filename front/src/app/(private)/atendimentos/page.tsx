"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AlertTriangle, Inbox, ShieldAlert } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { toast } from "sonner"
import { TableSkeleton } from "@/components/common/LoadingSkeletons"
import { PriorityBadge } from "@/components/atendimento/PriorityBadge"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import type { AtendimentoFilaCard, Prioridade } from "@/types/atendimento"

const ANALISE_LABELS: Record<string, string> = {
  pendente: "Pendente",
  processando: "Processando",
  erro: "Erro na análise",
}

function formatTempoEspera(totalMinutes: number) {
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = Math.floor(totalMinutes % 60)

  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  parts.push(`${minutes}min`)
  return parts.join(" ")
}

export default function AtendimentosPage() {
  const router = useRouter()
  const [fila, setFila] = useState<AtendimentoFilaCard[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [prioridadeFiltro, setPrioridadeFiltro] = useState<string>("all")

  const fetchFila = useCallback(async () => {
    try {
      const data = await atendimentoAdminService.getFila()
      setFila(data)
    } catch (error) {
      console.error("Erro ao carregar fila:", error)
      toast.error("Erro ao carregar fila de atendimento")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchFila()
    const interval = setInterval(fetchFila, 15000)
    return () => clearInterval(interval)
  }, [fetchFila])

  // Filtros são só de redução visual -- a ordem de prioridade vem do
  // backend (regra crítica -> P1..P4 -> índice AHP -> tempo de espera) e
  // nunca é recalculada no cliente.
  const filtrada = fila.filter((item) => {
    const matchesSearch =
      !searchTerm ||
      item.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.assunto.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesPrioridade = prioridadeFiltro === "all" || item.prioridade === (prioridadeFiltro as Prioridade)
    return matchesSearch && matchesPrioridade
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Atendimentos</h1>
        <p className="text-muted-foreground">Fila de atendimento priorizada em tempo real</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
          <CardDescription>Busque por nome ou assunto, ou filtre por prioridade</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="Buscar por nome ou assunto..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={prioridadeFiltro} onValueChange={setPrioridadeFiltro}>
              <SelectTrigger className="w-[220px]">
                <SelectValue placeholder="Filtrar por prioridade" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as prioridades</SelectItem>
                <SelectItem value="p1">P1 · Crítico</SelectItem>
                <SelectItem value="p2">P2 · Alto</SelectItem>
                <SelectItem value="p3">P3 · Médio</SelectItem>
                <SelectItem value="p4">P4 · Baixo</SelectItem>
                <SelectItem value="nao_classificado">Não classificado</SelectItem>
                <SelectItem value="revisao_humana">Revisão humana</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Fila</CardTitle>
          <CardDescription>{filtrada.length} atendimento(s) na fila</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <TableSkeleton rows={6} columns={6} />
          ) : filtrada.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Inbox className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Nenhum atendimento na fila</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cliente</TableHead>
                    <TableHead>Assunto</TableHead>
                    <TableHead>Prioridade</TableHead>
                    <TableHead>Tempo de espera</TableHead>
                    <TableHead>Atendente</TableHead>
                    <TableHead>Alertas</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtrada.map((item) => (
                    <TableRow
                      key={item.id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/atendimentos/${item.id}`)}
                    >
                      <TableCell className="font-medium">{item.nome}</TableCell>
                      <TableCell className="max-w-[260px] truncate">{item.assunto || "—"}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <PriorityBadge prioridade={item.prioridade} />
                          {item.analise_ia_status !== "concluida" && (
                            <Badge variant="outline" className="text-xs">
                              {ANALISE_LABELS[item.analise_ia_status] ?? item.analise_ia_status}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{formatTempoEspera(item.tempo_espera_minutos)}</TableCell>
                      <TableCell>{item.atendente?.name ?? "Não atribuído"}</TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center gap-2">
                          {item.dados_ausentes && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <AlertTriangle className="h-4 w-4 text-amber-500" />
                              </TooltipTrigger>
                              <TooltipContent>Dados ausentes</TooltipContent>
                            </Tooltip>
                          )}
                          {item.regra_critica_confirmada && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <ShieldAlert className="h-4 w-4 text-red-600" />
                              </TooltipTrigger>
                              <TooltipContent>Regra crítica confirmada</TooltipContent>
                            </Tooltip>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
