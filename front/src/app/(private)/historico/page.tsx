"use client"

import { useState, useEffect, useCallback } from "react"
import { Loader2, Search, RefreshCw } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { chamadoAdminService, type Chamado } from "@/services/chamado-admin.service"

const prioridadeVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  baixa: "secondary",
  media: "default",
  alta: "destructive",
  urgente: "destructive",
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "—"
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function HistoricoPage() {
  const [chamados, setChamados] = useState<Chamado[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")

  const fetchHistorico = useCallback(async () => {
    setIsLoading(true)
    try {
      const data = await chamadoAdminService.listHistorico({
        search: searchTerm || undefined,
        ordering: "-resolved_at",
      })
      setChamados(data || [])
    } catch (err) {
      console.error("Erro ao carregar historico:", err)
      setChamados([])
    } finally {
      setIsLoading(false)
    }
  }, [searchTerm])

  useEffect(() => {
    fetchHistorico()
  }, [fetchHistorico])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    fetchHistorico()
  }

  const handleRowClick = (chamado: Chamado) => {
    window.open(`/chamados/${chamado.id}`, "_blank", "noopener,noreferrer")
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Histórico de Chamados</h1>
          <p className="text-muted-foreground">
            Chamados concluídos há mais de 30 dias
          </p>
        </div>
        <Button onClick={fetchHistorico} variant="outline" size="sm">
          <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="max-w-md">
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

      {/* Table */}
      <div className="rounded-md border">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : chamados.length === 0 ? (
          <div className="flex items-center justify-center py-16 text-muted-foreground">
            Nenhum chamado encontrado no histórico.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Protocolo</TableHead>
                <TableHead>Assunto</TableHead>
                <TableHead>Solicitante</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Prioridade</TableHead>
                <TableHead>Resolvido em</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {chamados.map((chamado) => (
                <TableRow
                  key={chamado.id}
                  className="cursor-pointer"
                  onClick={() => handleRowClick(chamado)}
                >
                  <TableCell className="font-medium">#{chamado.protocolo}</TableCell>
                  <TableCell className="max-w-[300px] truncate">{chamado.assunto}</TableCell>
                  <TableCell>{chamado.nome}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{chamado.tipo_display}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={prioridadeVariant[chamado.prioridade] || "default"}>
                      {chamado.prioridade_display}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDate(chamado.resolved_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}
