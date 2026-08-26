"use client"

import { useEffect, useState } from "react"
import { Edit, Plus, Trash2 } from "lucide-react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { TableSkeleton } from "@/components/common/LoadingSkeletons"
import { ahpService } from "@/services/ahp.service"
import { IntensidadeDialog } from "@/components/ahp/IntensidadeDialog"
import type { Criterio, Intensidade } from "@/types/ahp"

export function IntensidadesPanel() {
  const [intensidades, setIntensidades] = useState<Intensidade[]>([])
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [criterioFiltro, setCriterioFiltro] = useState("all")
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [selected, setSelected] = useState<Intensidade | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [listaIntensidades, listaCriterios] = await Promise.all([
        ahpService.listIntensidades(),
        ahpService.listCriterios(),
      ])
      setIntensidades(listaIntensidades)
      setCriterios(listaCriterios)
    } catch {
      toast.error("Erro ao carregar intensidades")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleCreate = () => {
    setSelected(null)
    setIsDialogOpen(true)
  }

  const handleEdit = (intensidade: Intensidade) => {
    setSelected(intensidade)
    setIsDialogOpen(true)
  }

  const handleDelete = async (intensidade: Intensidade) => {
    if (!confirm(`Tem certeza que deseja excluir a intensidade "${intensidade.nome}"?`)) return
    const response = await ahpService.deleteIntensidade(intensidade.id)
    if (response.success) {
      toast.success("Intensidade excluída com sucesso")
      fetchData()
    } else {
      toast.error(response.message || "Erro ao excluir intensidade")
    }
  }

  const criterioNome = (id: number) => criterios.find((c) => c.id === id)?.nome ?? "—"

  const filtradas = intensidades.filter(
    (i) => criterioFiltro === "all" || i.criterio === Number(criterioFiltro)
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Select value={criterioFiltro} onValueChange={setCriterioFiltro}>
          <SelectTrigger className="w-[240px]">
            <SelectValue placeholder="Filtrar por critério" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os critérios</SelectItem>
            {criterios.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>{c.nome}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nova Intensidade
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} columns={5} />
      ) : filtradas.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">Nenhuma intensidade encontrada</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Critério</TableHead>
                <TableHead>Código</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtradas.map((i) => (
                <TableRow key={i.id}>
                  <TableCell className="font-medium">{i.nome}</TableCell>
                  <TableCell>{criterioNome(i.criterio)}</TableCell>
                  <TableCell><Badge variant="outline">{i.codigo_display}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={i.ativo ? "default" : "secondary"}>{i.ativo ? "Ativo" : "Inativo"}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(i)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(i)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <IntensidadeDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        intensidade={selected}
        criterios={criterios}
        onSave={fetchData}
      />
    </div>
  )
}
