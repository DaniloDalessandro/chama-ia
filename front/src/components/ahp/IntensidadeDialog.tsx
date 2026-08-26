"use client"

import { useEffect, useState } from "react"
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
import { Textarea } from "@/components/ui/textarea"
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
import type { Criterio, Intensidade, IntensidadeCodigo } from "@/types/ahp"

interface IntensidadeFormData {
  criterio: string
  nome: string
  codigo: IntensidadeCodigo
  descricao: string
  ordem: number
  orientacoes_para_ia: string
  exemplo_positivo: string
  exemplo_negativo: string
  ativo: boolean
}

const CODIGOS: { value: IntensidadeCodigo; label: string }[] = [
  { value: "ausente", label: "Ausente" },
  { value: "muito_baixa", label: "Muito Baixa" },
  { value: "baixa", label: "Baixa" },
  { value: "moderada", label: "Moderada" },
  { value: "alta", label: "Alta" },
  { value: "critica", label: "Crítica" },
  { value: "inconclusiva", label: "Inconclusiva" },
]

const emptyForm = (defaultCriterioId?: number): IntensidadeFormData => ({
  criterio: defaultCriterioId ? String(defaultCriterioId) : "",
  nome: "",
  codigo: "moderada",
  descricao: "",
  ordem: 0,
  orientacoes_para_ia: "",
  exemplo_positivo: "",
  exemplo_negativo: "",
  ativo: true,
})

interface IntensidadeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  intensidade: Intensidade | null
  criterios: Criterio[]
  onSave: () => void
}

export function IntensidadeDialog({
  open,
  onOpenChange,
  intensidade,
  criterios,
  onSave,
}: IntensidadeDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<IntensidadeFormData>(emptyForm())

  useEffect(() => {
    if (intensidade) {
      setFormData({
        criterio: String(intensidade.criterio),
        nome: intensidade.nome,
        codigo: intensidade.codigo,
        descricao: intensidade.descricao,
        ordem: intensidade.ordem,
        orientacoes_para_ia: intensidade.orientacoes_para_ia,
        exemplo_positivo: intensidade.exemplo_positivo,
        exemplo_negativo: intensidade.exemplo_negativo,
        ativo: intensidade.ativo,
      })
    } else {
      setFormData(emptyForm())
    }
  }, [intensidade, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.criterio) {
      toast.error("Selecione um critério")
      return
    }
    if (!formData.nome.trim()) {
      toast.error("Nome é obrigatório")
      return
    }

    setLoading(true)
    try {
      const payload = { ...formData, criterio: Number(formData.criterio) }
      const response = intensidade
        ? await ahpService.updateIntensidade(intensidade.id, payload)
        : await ahpService.createIntensidade(payload)

      if (response.success) {
        toast.success(intensidade ? "Intensidade atualizada com sucesso" : "Intensidade cadastrada com sucesso")
        onSave()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao salvar intensidade")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{intensidade ? "Editar Intensidade" : "Nova Intensidade"}</DialogTitle>
          <DialogDescription>
            {intensidade ? "Atualize os dados da intensidade" : "Preencha os dados para cadastrar uma nova intensidade"}
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
                onValueChange={(value) => setFormData({ ...formData, criterio: value })}
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

            <div className="col-span-2">
              <Label htmlFor="nome">
                Nome <span className="text-destructive">*</span>
              </Label>
              <Input
                id="nome"
                value={formData.nome}
                onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                required
              />
            </div>

            <div>
              <Label htmlFor="codigo">Código</Label>
              <Select
                value={formData.codigo}
                onValueChange={(value) => setFormData({ ...formData, codigo: value as IntensidadeCodigo })}
              >
                <SelectTrigger id="codigo">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CODIGOS.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
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

            <div className="col-span-2">
              <Label htmlFor="descricao">Descrição</Label>
              <Textarea
                id="descricao"
                value={formData.descricao}
                onChange={(e) => setFormData({ ...formData, descricao: e.target.value })}
                rows={2}
              />
            </div>

            <div className="col-span-2">
              <Label htmlFor="orientacoes_para_ia">Orientações para a IA</Label>
              <Textarea
                id="orientacoes_para_ia"
                value={formData.orientacoes_para_ia}
                onChange={(e) => setFormData({ ...formData, orientacoes_para_ia: e.target.value })}
                rows={2}
              />
            </div>

            <div>
              <Label htmlFor="exemplo_positivo">Exemplo positivo</Label>
              <Textarea
                id="exemplo_positivo"
                value={formData.exemplo_positivo}
                onChange={(e) => setFormData({ ...formData, exemplo_positivo: e.target.value })}
                rows={2}
              />
            </div>

            <div>
              <Label htmlFor="exemplo_negativo">Exemplo negativo</Label>
              <Textarea
                id="exemplo_negativo"
                value={formData.exemplo_negativo}
                onChange={(e) => setFormData({ ...formData, exemplo_negativo: e.target.value })}
                rows={2}
              />
            </div>

            <div className="col-span-2 flex items-center justify-between rounded-lg border p-3">
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
              {loading ? "Salvando..." : intensidade ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
