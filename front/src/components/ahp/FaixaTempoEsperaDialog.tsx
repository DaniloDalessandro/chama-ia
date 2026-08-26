"use client"

import { useEffect, useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { ahpService } from "@/services/ahp.service"
import type { Criterio, FaixaTempoEspera, Intensidade } from "@/types/ahp"

interface FaixaFormData {
  criterio: string
  minutos_min: number
  minutos_max: number | null
  semLimite: boolean
  intensidade: string
  ordem: number
  ativo: boolean
}

function emptyForm(defaultCriterioId?: number): FaixaFormData {
  return {
    criterio: defaultCriterioId ? String(defaultCriterioId) : "",
    minutos_min: 0,
    minutos_max: null,
    semLimite: false,
    intensidade: "",
    ordem: 0,
    ativo: true,
  }
}

interface FaixaTempoEsperaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  faixa: FaixaTempoEspera | null
  criterios: Criterio[]
  intensidades: Intensidade[]
  onSave: () => void
}

export function FaixaTempoEsperaDialog({
  open,
  onOpenChange,
  faixa,
  criterios,
  intensidades,
  onSave,
}: FaixaTempoEsperaDialogProps) {
  const [loading, setLoading] = useState(false)

  const criterioTempoEspera = useMemo(
    () => criterios.find((c) => c.codigo === "TEMPO_DE_ESPERA"),
    [criterios]
  )

  const [formData, setFormData] = useState<FaixaFormData>(emptyForm(criterioTempoEspera?.id))

  useEffect(() => {
    if (faixa) {
      setFormData({
        criterio: String(faixa.criterio),
        minutos_min: faixa.minutos_min,
        minutos_max: faixa.minutos_max,
        semLimite: faixa.minutos_max === null,
        intensidade: String(faixa.intensidade),
        ordem: faixa.ordem,
        ativo: faixa.ativo,
      })
    } else {
      setFormData(emptyForm(criterioTempoEspera?.id))
    }
  }, [faixa, open, criterioTempoEspera])

  const intensidadesDoCriterio = intensidades.filter(
    (i) => formData.criterio && i.criterio === Number(formData.criterio)
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.criterio) {
      toast.error("Selecione um critério")
      return
    }
    if (!formData.intensidade) {
      toast.error("Selecione uma intensidade")
      return
    }
    if (!formData.semLimite && formData.minutos_max !== null && formData.minutos_max <= formData.minutos_min) {
      toast.error("Minutos (max) precisa ser maior que minutos (min)")
      return
    }

    setLoading(true)
    try {
      const payload = {
        criterio: Number(formData.criterio),
        minutos_min: formData.minutos_min,
        minutos_max: formData.semLimite ? null : formData.minutos_max,
        intensidade: Number(formData.intensidade),
        ordem: formData.ordem,
        ativo: formData.ativo,
      }
      const response = faixa
        ? await ahpService.updateFaixaTempoEspera(faixa.id, payload)
        : await ahpService.createFaixaTempoEspera(payload)

      if (response.success) {
        toast.success(faixa ? "Faixa atualizada com sucesso" : "Faixa cadastrada com sucesso")
        onSave()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao salvar faixa")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{faixa ? "Editar Faixa de Tempo de Espera" : "Nova Faixa de Tempo de Espera"}</DialogTitle>
          <DialogDescription>
            {faixa ? "Atualize a faixa de tempo" : "Preencha os dados para cadastrar uma nova faixa"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label htmlFor="criterio">
                Critério <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.criterio}
                onValueChange={(value) => setFormData({ ...formData, criterio: value, intensidade: "" })}
              >
                <SelectTrigger id="criterio">
                  <SelectValue placeholder="Selecione o critério" />
                </SelectTrigger>
                <SelectContent>
                  {criterios.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="minutos_min">Minutos (min)</Label>
              <Input
                id="minutos_min"
                type="number"
                min={0}
                value={formData.minutos_min}
                onChange={(e) => setFormData({ ...formData, minutos_min: Number(e.target.value) })}
              />
            </div>

            <div>
              <Label htmlFor="minutos_max">Minutos (max)</Label>
              <Input
                id="minutos_max"
                type="number"
                min={0}
                value={formData.minutos_max ?? ""}
                disabled={formData.semLimite}
                onChange={(e) =>
                  setFormData({ ...formData, minutos_max: e.target.value ? Number(e.target.value) : null })
                }
              />
            </div>

            <div className="col-span-2 flex items-center justify-between rounded-lg border p-3">
              <Label htmlFor="semLimite" className="cursor-pointer">Sem limite superior</Label>
              <Switch
                id="semLimite"
                checked={formData.semLimite}
                onCheckedChange={(checked) =>
                  setFormData({ ...formData, semLimite: checked, minutos_max: checked ? null : formData.minutos_max })
                }
              />
            </div>

            <div className="col-span-2">
              <Label htmlFor="intensidade">
                Intensidade <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.intensidade}
                onValueChange={(value) => setFormData({ ...formData, intensidade: value })}
              >
                <SelectTrigger id="intensidade">
                  <SelectValue placeholder="Selecione a intensidade" />
                </SelectTrigger>
                <SelectContent>
                  {intensidadesDoCriterio.map((i) => (
                    <SelectItem key={i.id} value={String(i.id)}>
                      {i.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="ordem">Ordem</Label>
              <Input
                id="ordem"
                type="number"
                value={formData.ordem}
                onChange={(e) => setFormData({ ...formData, ordem: Number(e.target.value) })}
              />
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <Label htmlFor="ativo" className="cursor-pointer">Ativo</Label>
              <Switch
                id="ativo"
                checked={formData.ativo}
                onCheckedChange={(checked) => setFormData({ ...formData, ativo: checked })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Salvando..." : faixa ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
