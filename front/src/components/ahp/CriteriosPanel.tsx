"use client"

import { useEffect, useState } from "react"
import { Copy, Edit, History, Plus, Trash2, ToggleLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import { CriterioDialog } from "@/components/ahp/CriterioDialog"
import type { Criterio, VersaoAHP } from "@/types/ahp"

export function CriteriosPanel() {
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [selected, setSelected] = useState<Criterio | null>(null)
  const [historico, setHistorico] = useState<{
    criado_em: string
    atualizado_em: string
    atualizado_por: string | null
    versoes_ahp_participadas: VersaoAHP[]
  } | null>(null)
  const [isHistoricoOpen, setIsHistoricoOpen] = useState(false)

  const fetchCriterios = async () => {
    try {
      setLoading(true)
      const data = await ahpService.listCriterios()
      setCriterios(data)
    } catch {
      toast.error("Erro ao carregar critérios")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCriterios()
  }, [])

  const handleCreate = () => {
    setSelected(null)
    setIsDialogOpen(true)
  }

  const handleEdit = (criterio: Criterio) => {
    setSelected(criterio)
    setIsDialogOpen(true)
  }

  const handleDelete = async (criterio: Criterio) => {
    if (!confirm(`Tem certeza que deseja excluir o critério "${criterio.nome}"?`)) return
    const response = await ahpService.deleteCriterio(criterio.id)
    if (response.success) {
      toast.success("Critério excluído com sucesso")
      fetchCriterios()
    } else {
      toast.error(response.message || "Erro ao excluir critério")
    }
  }

  const handleInativar = async (criterio: Criterio) => {
    const response = await ahpService.inativarCriterio(criterio.id)
    if (response.success) {
      toast.success("Critério inativado")
      fetchCriterios()
    } else {
      toast.error(response.message || "Erro ao inativar critério")
    }
  }

  const handleDuplicar = async (criterio: Criterio) => {
    const response = await ahpService.duplicarCriterio(criterio.id)
    if (response.success) {
      toast.success("Critério duplicado")
      fetchCriterios()
    } else {
      toast.error(response.message || "Erro ao duplicar critério")
    }
  }

  const handleHistorico = async (criterio: Criterio) => {
    const data = await ahpService.getCriterioHistorico(criterio.id)
    setHistorico(data)
    setIsHistoricoOpen(true)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{criterios.length} critério(s) cadastrado(s)</p>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Novo Critério
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} columns={6} />
      ) : criterios.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">Nenhum critério cadastrado</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Critério</TableHead>
                <TableHead>Código</TableHead>
                <TableHead>Importância</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {criterios.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium">
                    <span className="inline-flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full border"
                        style={{ backgroundColor: c.cor_identificacao }}
                      />
                      {c.nome}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{c.codigo}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{c.importancia_negocio}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={c.ativo ? "default" : "secondary"}>{c.ativo ? "Ativo" : "Inativo"}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="icon" onClick={() => handleHistorico(c)} title="Ver histórico">
                        <History className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDuplicar(c)} title="Duplicar">
                        <Copy className="h-4 w-4" />
                      </Button>
                      {c.ativo && (
                        <Button variant="ghost" size="icon" onClick={() => handleInativar(c)} title="Inativar">
                          <ToggleLeft className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(c)} title="Editar">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(c)} title="Excluir">
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

      <CriterioDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        criterio={selected}
        onSave={fetchCriterios}
      />

      <Dialog open={isHistoricoOpen} onOpenChange={setIsHistoricoOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Histórico do Critério</DialogTitle>
          </DialogHeader>
          {historico && (
            <div className="space-y-3 text-sm">
              <p><span className="text-muted-foreground">Criado em:</span> {new Date(historico.criado_em).toLocaleString("pt-BR")}</p>
              <p><span className="text-muted-foreground">Atualizado em:</span> {new Date(historico.atualizado_em).toLocaleString("pt-BR")}</p>
              <p><span className="text-muted-foreground">Atualizado por:</span> {historico.atualizado_por || "—"}</p>
              <div>
                <p className="mb-1 font-medium">Versões AHP que utilizaram este critério</p>
                {historico.versoes_ahp_participadas.length === 0 ? (
                  <p className="text-muted-foreground">Nenhuma</p>
                ) : (
                  <ul className="list-disc space-y-1 pl-5">
                    {historico.versoes_ahp_participadas.map((v) => (
                      <li key={v.id}>Versão {v.numero_versao} — {v.estado}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
