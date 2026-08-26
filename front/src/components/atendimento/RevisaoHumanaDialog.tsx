"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import type { Prioridade } from "@/types/atendimento"

interface RevisaoHumanaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  atendimentoId: number
  onSuccess: () => void
}

export function RevisaoHumanaDialog({ open, onOpenChange, atendimentoId, onSuccess }: RevisaoHumanaDialogProps) {
  const [novaPrioridade, setNovaPrioridade] = useState<Prioridade>("p3")
  const [justificativa, setJustificativa] = useState("")
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!justificativa.trim()) {
      toast.error("Justificativa é obrigatória")
      return
    }

    setLoading(true)
    try {
      const response = await atendimentoAdminService.revisaoHumana(atendimentoId, {
        nova_prioridade: novaPrioridade,
        justificativa,
      })
      if (response.success) {
        toast.success("Revisão humana registrada")
        setJustificativa("")
        onSuccess()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao registrar revisão")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Revisão humana de prioridade</DialogTitle>
          <DialogDescription>Sobrescreva manualmente a prioridade deste atendimento.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="nova_prioridade">Nova prioridade</Label>
            <Select value={novaPrioridade} onValueChange={(value) => setNovaPrioridade(value as Prioridade)}>
              <SelectTrigger id="nova_prioridade">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="p1">P1 · Crítico</SelectItem>
                <SelectItem value="p2">P2 · Alto</SelectItem>
                <SelectItem value="p3">P3 · Médio</SelectItem>
                <SelectItem value="p4">P4 · Baixo</SelectItem>
                <SelectItem value="nao_classificado">Não classificado</SelectItem>
                <SelectItem value="revisao_humana">Revisão humana</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="justificativa">
              Justificativa <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="justificativa"
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
              rows={3}
              placeholder="Explique o motivo da revisão manual..."
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? "Salvando..." : "Confirmar revisão"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
