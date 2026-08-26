"use client"

import { useEffect, useState } from "react"
import { Check, Edit, Plus, Trash2, X } from "lucide-react"
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
import { TermoDialog } from "@/components/ahp/TermoDialog"
import type { Criterio, Intensidade, Termo } from "@/types/ahp"

const STATUS_LABELS: Record<Termo["status_aprovacao"], string> = {
  pendente_aprovacao: "Pendente",
  aprovado: "Aprovado",
  rejeitado: "Rejeitado",
}

const STATUS_VARIANTS: Record<Termo["status_aprovacao"], "default" | "secondary" | "destructive"> = {
  pendente_aprovacao: "secondary",
  aprovado: "default",
  rejeitado: "destructive",
}

export function TermosPanel() {
  const [termos, setTermos] = useState<Termo[]>([])
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [intensidades, setIntensidades] = useState<Intensidade[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [selected, setSelected] = useState<Termo | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [listaTermos, listaCriterios, listaIntensidades] = await Promise.all([
        ahpService.listTermos(),
        ahpService.listCriterios(),
        ahpService.listIntensidades(),
      ])
      setTermos(listaTermos)
      setCriterios(listaCriterios)
      setIntensidades(listaIntensidades)
    } catch {
      toast.error("Erro ao carregar termos")
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

  const handleEdit = (termo: Termo) => {
    setSelected(termo)
    setIsDialogOpen(true)
  }

  const handleDelete = async (termo: Termo) => {
    if (!confirm(`Tem certeza que deseja excluir o termo "${termo.termo}"?`)) return
    const response = await ahpService.deleteTermo(termo.id)
    if (response.success) {
      toast.success("Termo excluído com sucesso")
      fetchData()
    } else {
      toast.error(response.message || "Erro ao excluir termo")
    }
  }

  const handleAprovar = async (termo: Termo) => {
    const response = await ahpService.aprovarTermo(termo.id)
    if (response.success) {
      toast.success("Termo aprovado")
      fetchData()
    } else {
      toast.error(response.message || "Erro ao aprovar termo")
    }
  }

  const handleRejeitar = async (termo: Termo) => {
    const response = await ahpService.rejeitarTermo(termo.id)
    if (response.success) {
      toast.success("Termo rejeitado")
      fetchData()
    } else {
      toast.error(response.message || "Erro ao rejeitar termo")
    }
  }

  const criterioNome = (id: number) => criterios.find((c) => c.id === id)?.nome ?? "—"

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{termos.length} termo(s) cadastrado(s)</p>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Novo Termo
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} columns={5} />
      ) : termos.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">Nenhum termo cadastrado</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Termo</TableHead>
                <TableHead>Critério</TableHead>
                <TableHead>Status de aprovação</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {termos.map((t) => (
                <TableRow key={t.id}>
                  <TableCell className="font-medium">{t.termo}</TableCell>
                  <TableCell>{criterioNome(t.criterio)}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANTS[t.status_aprovacao]}>{STATUS_LABELS[t.status_aprovacao]}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {t.status_aprovacao === "pendente_aprovacao" && (
                        <>
                          <Button variant="ghost" size="icon" onClick={() => handleAprovar(t)} title="Aprovar">
                            <Check className="h-4 w-4 text-green-600" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleRejeitar(t)} title="Rejeitar">
                            <X className="h-4 w-4 text-destructive" />
                          </Button>
                        </>
                      )}
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(t)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(t)}>
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

      <TermoDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        termo={selected}
        criterios={criterios}
        intensidades={intensidades}
        onSave={fetchData}
      />
    </div>
  )
}
