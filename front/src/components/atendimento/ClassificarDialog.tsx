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
import { toast } from "sonner"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"

interface ClassificarDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  atendimentoId: number
  onSuccess: () => void
}

export function ClassificarDialog({ open, onOpenChange, atendimentoId, onSuccess }: ClassificarDialogProps) {
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try {
      const response = await atendimentoAdminService.classificar(atendimentoId)
      if (response.success) {
        toast.success("Atendimento reclassificado")
        onSuccess()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao classificar atendimento")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reclassificar atendimento</DialogTitle>
          <DialogDescription>
            A IA irá reanalisar este atendimento e recalcular sua prioridade com base nas informações mais
            recentes.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={handleConfirm} disabled={loading}>
            {loading ? "Classificando..." : "Reclassificar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
