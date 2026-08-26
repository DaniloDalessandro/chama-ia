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
import type { Criterio, ImportanciaNegocio, Orientacao } from "@/types/ahp"

interface CriterioFormData {
  nome: string
  codigo: string
  descricao: string
  orientacao: Orientacao
  ordem: number
  ativo: boolean
  importancia_negocio: ImportanciaNegocio
  regra_critica: boolean
  exige_revisao_humana: boolean
  permite_deteccao_semantica: boolean
  orientacoes_para_ia: string
  exemplos_positivos: string
  exemplos_negativos: string
  cor_identificacao: string
  icone: string
}

const EMPTY_FORM: CriterioFormData = {
  nome: "",
  codigo: "",
  descricao: "",
  orientacao: "positiva",
  ordem: 0,
  ativo: true,
  importancia_negocio: "media",
  regra_critica: false,
  exige_revisao_humana: false,
  permite_deteccao_semantica: true,
  orientacoes_para_ia: "",
  exemplos_positivos: "",
  exemplos_negativos: "",
  cor_identificacao: "#64748B",
  icone: "",
}

interface CriterioDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  criterio: Criterio | null
  onSave: () => void
}

export function CriterioDialog({ open, onOpenChange, criterio, onSave }: CriterioDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<CriterioFormData>(EMPTY_FORM)

  useEffect(() => {
    if (criterio) {
      setFormData({
        nome: criterio.nome,
        codigo: criterio.codigo,
        descricao: criterio.descricao,
        orientacao: criterio.orientacao,
        ordem: criterio.ordem,
        ativo: criterio.ativo,
        importancia_negocio: criterio.importancia_negocio,
        regra_critica: criterio.regra_critica,
        exige_revisao_humana: criterio.exige_revisao_humana,
        permite_deteccao_semantica: criterio.permite_deteccao_semantica,
        orientacoes_para_ia: criterio.orientacoes_para_ia,
        exemplos_positivos: criterio.exemplos_positivos,
        exemplos_negativos: criterio.exemplos_negativos,
        cor_identificacao: criterio.cor_identificacao,
        icone: criterio.icone,
      })
    } else {
      setFormData(EMPTY_FORM)
    }
  }, [criterio, open])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.nome.trim()) {
      toast.error("Nome é obrigatório")
      return
    }
    if (!formData.codigo.trim()) {
      toast.error("Código é obrigatório")
      return
    }

    setLoading(true)
    try {
      const response = criterio
        ? await ahpService.updateCriterio(criterio.id, formData)
        : await ahpService.createCriterio(formData)

      if (response.success) {
        toast.success(criterio ? "Critério atualizado com sucesso" : "Critério cadastrado com sucesso")
        onSave()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao salvar critério")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{criterio ? "Editar Critério" : "Novo Critério"}</DialogTitle>
          <DialogDescription>
            {criterio ? "Atualize as informações do critério" : "Preencha os dados para cadastrar um novo critério"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Label htmlFor="nome">
                Nome <span className="text-destructive">*</span>
              </Label>
              <Input
                id="nome"
                value={formData.nome}
                onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                placeholder="Ex: Urgência"
                required
              />
            </div>

            <div>
              <Label htmlFor="codigo">
                Código <span className="text-destructive">*</span>
              </Label>
              <Input
                id="codigo"
                value={formData.codigo}
                onChange={(e) => setFormData({ ...formData, codigo: e.target.value.toUpperCase() })}
                placeholder="Ex: URGENCIA"
                required
                disabled={!!criterio}
              />
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

            <div>
              <Label htmlFor="orientacao">Orientação</Label>
              <Select
                value={formData.orientacao}
                onValueChange={(value) => setFormData({ ...formData, orientacao: value as Orientacao })}
              >
                <SelectTrigger id="orientacao">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="positiva">Positiva (intensidade maior = maior prioridade)</SelectItem>
                  <SelectItem value="negativa">Negativa (intensidade maior = menor prioridade)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="importancia_negocio">Importância para o negócio</Label>
              <Select
                value={formData.importancia_negocio}
                onValueChange={(value) =>
                  setFormData({ ...formData, importancia_negocio: value as ImportanciaNegocio })
                }
              >
                <SelectTrigger id="importancia_negocio">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="baixa">Baixa</SelectItem>
                  <SelectItem value="media">Média</SelectItem>
                  <SelectItem value="alta">Alta</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="cor_identificacao">Cor de identificação</Label>
              <div className="flex items-center gap-2">
                <input
                  id="cor_identificacao"
                  type="color"
                  value={formData.cor_identificacao}
                  onChange={(e) => setFormData({ ...formData, cor_identificacao: e.target.value })}
                  className="h-9 w-12 cursor-pointer rounded border"
                />
                <Input
                  value={formData.cor_identificacao}
                  onChange={(e) => setFormData({ ...formData, cor_identificacao: e.target.value })}
                  className="flex-1"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="icone">Ícone (nome lucide-react)</Label>
              <Input
                id="icone"
                value={formData.icone}
                onChange={(e) => setFormData({ ...formData, icone: e.target.value })}
                placeholder="Ex: AlertTriangle"
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
              <Label htmlFor="exemplos_positivos">Exemplos positivos</Label>
              <Textarea
                id="exemplos_positivos"
                value={formData.exemplos_positivos}
                onChange={(e) => setFormData({ ...formData, exemplos_positivos: e.target.value })}
                rows={2}
              />
            </div>

            <div>
              <Label htmlFor="exemplos_negativos">Exemplos negativos</Label>
              <Textarea
                id="exemplos_negativos"
                value={formData.exemplos_negativos}
                onChange={(e) => setFormData({ ...formData, exemplos_negativos: e.target.value })}
                rows={2}
              />
            </div>

            <div className="col-span-2 grid grid-cols-2 gap-3 rounded-lg border p-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="ativo" className="cursor-pointer">Ativo</Label>
                <Switch
                  id="ativo"
                  checked={formData.ativo}
                  onCheckedChange={(checked) => setFormData({ ...formData, ativo: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="regra_critica" className="cursor-pointer">Regra crítica</Label>
                <Switch
                  id="regra_critica"
                  checked={formData.regra_critica}
                  onCheckedChange={(checked) => setFormData({ ...formData, regra_critica: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="exige_revisao_humana" className="cursor-pointer">Exige revisão humana</Label>
                <Switch
                  id="exige_revisao_humana"
                  checked={formData.exige_revisao_humana}
                  onCheckedChange={(checked) => setFormData({ ...formData, exige_revisao_humana: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="permite_deteccao_semantica" className="cursor-pointer">Detecção semântica</Label>
                <Switch
                  id="permite_deteccao_semantica"
                  checked={formData.permite_deteccao_semantica}
                  onCheckedChange={(checked) => setFormData({ ...formData, permite_deteccao_semantica: checked })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Salvando..." : criterio ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
