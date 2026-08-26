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
import { toast } from "sonner"
import { TableSkeleton } from "@/components/common/LoadingSkeletons"
import { ahpService } from "@/services/ahp.service"
import { FaixaTempoEsperaDialog } from "@/components/ahp/FaixaTempoEsperaDialog"
import type { Criterio, FaixaTempoEspera, Intensidade } from "@/types/ahp"

export function FaixasTempoEsperaPanel() {
  const [faixas, setFaixas] = useState<FaixaTempoEspera[]>([])
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [intensidades, setIntensidades] = useState<Intensidade[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [selected, setSelected] = useState<FaixaTempoEspera | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [listaFaixas, listaCriterios, listaIntensidades] = await Promise.all([
        ahpService.listFaixasTempoEspera(),
        ahpService.listCriterios(),
        ahpService.listIntensidades(),
      ])
      setFaixas(listaFaixas)
      setCriterios(listaCriterios)
      setIntensidades(listaIntensidades)
    } catch {
      toast.error("Erro ao carregar faixas de tempo de espera")
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

  const handleEdit = (faixa: FaixaTempoEspera) => {
    setSelected(faixa)
    setIsDialogOpen(true)
  }

  const handleDelete = async (faixa: FaixaTempoEspera) => {
    if (!confirm("Tem certeza que deseja excluir esta faixa?")) return
    const response = await ahpService.deleteFaixaTempoEspera(faixa.id)
    if (response.success) {
      toast.success("Faixa excluída com sucesso")
      fetchData()
    } else {
      toast.error(response.message || "Erro ao excluir faixa")
    }
  }

  const intensidadeNome = (id: number) => intensidades.find((i) => i.id === id)?.nome ?? "—"

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{faixas.length} faixa(s) cadastrada(s)</p>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nova Faixa
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} columns={5} />
      ) : faixas.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">Nenhuma faixa cadastrada</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Faixa (minutos)</TableHead>
                <TableHead>Intensidade</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {faixas.map((f) => (
                <TableRow key={f.id}>
                  <TableCell className="font-medium">
                    {f.minutos_min} — {f.minutos_max ?? "sem limite"}
                  </TableCell>
                  <TableCell>{intensidadeNome(f.intensidade)}</TableCell>
                  <TableCell>
                    <Badge variant={f.ativo ? "default" : "secondary"}>{f.ativo ? "Ativo" : "Inativo"}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(f)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(f)}>
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

      <FaixaTempoEsperaDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        faixa={selected}
        criterios={criterios}
        intensidades={intensidades}
        onSave={fetchData}
      />
    </div>
  )
}
