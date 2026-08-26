"use client"

import { useEffect, useState } from "react"
import { Check, PlayCircle, Plus, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { EstadoVersaoBadge } from "@/components/ahp/EstadoVersaoBadge"
import { ConsistenciaBadge } from "@/components/ahp/ConsistenciaBadge"
import { VersaoAHPWizardDialog } from "@/components/ahp/VersaoAHPWizardDialog"
import type { VersaoAHP } from "@/types/ahp"

const CONTINUAVEIS: VersaoAHP["estado"][] = ["rascunho", "processando", "inconsistente", "erro"]

export function VersoesPanel() {
  const [versoes, setVersoes] = useState<VersaoAHP[]>([])
  const [loading, setLoading] = useState(true)
  const [isWizardOpen, setIsWizardOpen] = useState(false)
  const [resumeVersao, setResumeVersao] = useState<VersaoAHP | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingValue, setEditingValue] = useState("")

  const fetchVersoes = async () => {
    try {
      setLoading(true)
      const data = await ahpService.listVersoes()
      setVersoes(data)
    } catch {
      toast.error("Erro ao carregar versões AHP")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVersoes()
  }, [])

  const handleNovaVersao = () => {
    setResumeVersao(null)
    setIsWizardOpen(true)
  }

  const handleContinuar = (versao: VersaoAHP) => {
    setResumeVersao(versao)
    setIsWizardOpen(true)
  }

  const handleStartEdit = (versao: VersaoAHP) => {
    setEditingId(versao.id)
    setEditingValue(versao.descricao)
  }

  const handleSaveEdit = async (versao: VersaoAHP) => {
    const response = await ahpService.updateVersao(versao.id, editingValue)
    if (response.success) {
      toast.success("Descrição atualizada")
      setEditingId(null)
      fetchVersoes()
    } else {
      toast.error(response.message || "Erro ao atualizar descrição")
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{versoes.length} versão(ões) cadastrada(s)</p>
        <Button onClick={handleNovaVersao}>
          <Plus className="mr-2 h-4 w-4" />
          Nova Versão
        </Button>
      </div>

      {loading ? (
        <TableSkeleton rows={4} columns={5} />
      ) : versoes.length === 0 ? (
        <p className="py-8 text-center text-muted-foreground">Nenhuma versão cadastrada</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Versão</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Descrição</TableHead>
                <TableHead>Consistência</TableHead>
                <TableHead>Ativada em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {versoes.map((v) => (
                <TableRow key={v.id}>
                  <TableCell className="font-medium">#{v.numero_versao}</TableCell>
                  <TableCell><EstadoVersaoBadge estado={v.estado} /></TableCell>
                  <TableCell className="max-w-[220px]">
                    {editingId === v.id ? (
                      <div className="flex items-center gap-1">
                        <Input
                          value={editingValue}
                          onChange={(e) => setEditingValue(e.target.value)}
                          className="h-8"
                        />
                        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleSaveEdit(v)}>
                          <Check className="h-4 w-4 text-green-600" />
                        </Button>
                        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setEditingId(null)}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className="truncate text-left hover:underline disabled:cursor-default disabled:hover:no-underline"
                        disabled={v.estado !== "rascunho"}
                        onClick={() => v.estado === "rascunho" && handleStartEdit(v)}
                        title={v.estado === "rascunho" ? "Clique para editar" : v.descricao}
                      >
                        {v.descricao || "—"}
                      </button>
                    )}
                  </TableCell>
                  <TableCell><ConsistenciaBadge estado={v.estado} /></TableCell>
                  <TableCell>{v.ativada_em ? new Date(v.ativada_em).toLocaleDateString("pt-BR") : "—"}</TableCell>
                  <TableCell className="text-right">
                    {CONTINUAVEIS.includes(v.estado) && (
                      <Button variant="ghost" size="sm" onClick={() => handleContinuar(v)}>
                        <PlayCircle className="mr-1 h-4 w-4" />
                        Continuar
                      </Button>
                    )}
                    {v.mensagens_erro.length > 0 && (
                      <p className="mt-1 text-xs text-destructive">{v.mensagens_erro.join(" · ")}</p>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <VersaoAHPWizardDialog
        open={isWizardOpen}
        onOpenChange={setIsWizardOpen}
        resumeVersao={resumeVersao}
        onSave={fetchVersoes}
      />
    </div>
  )
}
