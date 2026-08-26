"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
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
import { toast } from "sonner"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"

interface EncaminharChamadoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  atendimentoId: number
  onSuccess: () => void
}

export function EncaminharChamadoDialog({
  open,
  onOpenChange,
  atendimentoId,
  onSuccess,
}: EncaminharChamadoDialogProps) {
  const router = useRouter()
  const [motivo, setMotivo] = useState("")
  const [loading, setLoading] = useState(false)
  const [protocolo, setProtocolo] = useState<{ id: number; protocolo: string } | null>(null)

  const handleSubmit = async () => {
    if (!motivo.trim()) {
      toast.error("Motivo é obrigatório")
      return
    }

    setLoading(true)
    try {
      const response = await atendimentoAdminService.encaminharChamado(atendimentoId, { motivo })
      if (response.success && response.data) {
        setProtocolo({ id: response.data.id, protocolo: response.data.protocolo })
        toast.success("Chamado criado com sucesso")
        onSuccess()
      } else {
        toast.error(response.message || "Erro ao encaminhar para chamado")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleClose = (nextOpen: boolean) => {
    onOpenChange(nextOpen)
    if (!nextOpen) {
      setMotivo("")
      setProtocolo(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        {protocolo ? (
          <>
            <DialogHeader>
              <DialogTitle>Chamado criado</DialogTitle>
              <DialogDescription>
                O atendimento foi encaminhado. Protocolo: <strong>{protocolo.protocolo}</strong>
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => handleClose(false)}>
                Fechar
              </Button>
              <Button onClick={() => router.push(`/chamados/${protocolo.id}`)}>Ver chamado</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Encaminhar para chamado</DialogTitle>
              <DialogDescription>
                Use quando o atendimento não puder ser resolvido no chat. Um novo Chamado será criado, vinculado
                a este atendimento.
              </DialogDescription>
            </DialogHeader>

            <div>
              <Label htmlFor="motivo">
                Motivo <span className="text-destructive">*</span>
              </Label>
              <Textarea
                id="motivo"
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
                rows={3}
                placeholder="Explique por que este atendimento precisa virar um chamado..."
              />
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => handleClose(false)} disabled={loading}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={loading}>
                {loading ? "Encaminhando..." : "Encaminhar"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
