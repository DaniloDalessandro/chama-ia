"use client"

import { useEffect, useState } from "react"
import { Edit } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { ahpService } from "@/services/ahp.service"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import type { AuditoriaClassificacaoSummary, AvaliacaoCriterioAtendimento } from "@/types/atendimento"
import type { Criterio, Intensidade } from "@/types/ahp"

interface AuditoriaSummaryCardProps {
  atendimentoId: number
  assunto: string
  resumo: string
  servicoAfetado: string
  indiceAhp: number | null
  avaliacoes: AvaliacaoCriterioAtendimento[]
  auditoriaMaisRecente: AuditoriaClassificacaoSummary | null
  onSaved: () => void
}

/**
 * Nunca destrutura campos numéricos de `auditoriaMaisRecente` além de
 * `id`/`criado_em` -- o tipo `AuditoriaClassificacaoSummary` já impede isso
 * em tempo de compilação (pesos/matrizes/CI/CR não existem no tipo).
 */
export function AuditoriaSummaryCard({
  atendimentoId,
  assunto,
  resumo,
  servicoAfetado,
  indiceAhp,
  avaliacoes,
  auditoriaMaisRecente,
  onSaved,
}: AuditoriaSummaryCardProps) {
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [intensidades, setIntensidades] = useState<Intensidade[]>([])
  const [editing, setEditing] = useState<AvaliacaoCriterioAtendimento | null>(null)
  const [intensidadeSelecionada, setIntensidadeSelecionada] = useState("")
  const [evidencia, setEvidencia] = useState("")
  const [justificativa, setJustificativa] = useState("")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    Promise.all([ahpService.listCriterios(), ahpService.listIntensidades()]).then(
      ([listaCriterios, listaIntensidades]) => {
        setCriterios(listaCriterios)
        setIntensidades(listaIntensidades)
      }
    )
  }, [])

  const criterioNome = (id: number) => criterios.find((c) => c.id === id)?.nome ?? `#${id}`
  const intensidadeNome = (id: number) => intensidades.find((i) => i.id === id)?.nome ?? `#${id}`

  const handleEdit = (avaliacao: AvaliacaoCriterioAtendimento) => {
    setEditing(avaliacao)
    setIntensidadeSelecionada(String(avaliacao.intensidade))
    setEvidencia(avaliacao.evidencia)
    setJustificativa(avaliacao.justificativa)
  }

  const handleSave = async () => {
    if (!editing) return
    setSaving(true)
    try {
      const response = await atendimentoAdminService.upsertAvaliacao(atendimentoId, {
        criterio: editing.criterio,
        intensidade: Number(intensidadeSelecionada),
        evidencia,
        justificativa,
      })
      if (response.success) {
        toast.success("Avaliação atualizada")
        setEditing(null)
        onSaved()
      } else {
        toast.error(response.message || "Erro ao atualizar avaliação")
      }
    } finally {
      setSaving(false)
    }
  }

  const intensidadesDoCriterio = editing
    ? intensidades.filter((i) => i.criterio === editing.criterio)
    : []

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Classificação</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <p className="text-muted-foreground">Assunto</p>
            <p className="font-medium">{assunto || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Serviço afetado</p>
            <p className="font-medium">{servicoAfetado || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Índice AHP</p>
            <p className="font-medium">{indiceAhp !== null ? indiceAhp.toFixed(2) : "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Última classificação</p>
            <p className="font-medium">
              {auditoriaMaisRecente ? new Date(auditoriaMaisRecente.criado_em).toLocaleString("pt-BR") : "—"}
            </p>
          </div>
        </div>

        {resumo && (
          <>
            <Separator />
            <div>
              <p className="text-sm text-muted-foreground mb-1">Resumo</p>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{resumo}</p>
            </div>
          </>
        )}

        <Separator />

        <div>
          <p className="mb-2 text-sm font-medium">Avaliações de critério</p>
          {avaliacoes.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhuma avaliação registrada ainda.</p>
          ) : (
            <div className="space-y-2">
              {avaliacoes.map((avaliacao) => (
                <div key={avaliacao.id} className="flex items-start justify-between rounded-lg border p-3 text-sm">
                  <div>
                    <p className="font-medium">
                      {criterioNome(avaliacao.criterio)} → {intensidadeNome(avaliacao.intensidade)}
                    </p>
                    {avaliacao.evidencia && (
                      <p className="mt-1 text-muted-foreground">{avaliacao.evidencia}</p>
                    )}
                    {avaliacao.dados_ausentes && (
                      <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">Dados ausentes</p>
                    )}
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => handleEdit(avaliacao)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>

      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar avaliação — {editing && criterioNome(editing.criterio)}</DialogTitle>
            <DialogDescription>Ajuste a intensidade e a evidência para este critério.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="intensidade">Intensidade</Label>
              <Select value={intensidadeSelecionada} onValueChange={setIntensidadeSelecionada}>
                <SelectTrigger id="intensidade">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {intensidadesDoCriterio.map((i) => (
                    <SelectItem key={i.id} value={String(i.id)}>{i.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="evidencia">Evidência</Label>
              <Textarea id="evidencia" value={evidencia} onChange={(e) => setEvidencia(e.target.value)} rows={2} />
            </div>
            <div>
              <Label htmlFor="justificativa">Justificativa</Label>
              <Textarea
                id="justificativa"
                value={justificativa}
                onChange={(e) => setJustificativa(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)} disabled={saving}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
