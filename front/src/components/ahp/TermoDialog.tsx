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
import type { Criterio, Intensidade, Termo, TipoCorrespondencia } from "@/types/ahp"

interface TermoFormData {
  criterio: string
  termo: string
  descricao: string
  tipo_correspondencia: TipoCorrespondencia
  intensidade_base: string
  exige_contexto: boolean
  regra_critica: boolean
  considerar_mensagem_atual: boolean
  considerar_historico: boolean
  considerar_anexos: boolean
  considerar_imagens: boolean
  ativo: boolean
}

const TIPOS: { value: TipoCorrespondencia; label: string }[] = [
  { value: "exato", label: "Exato" },
  { value: "contem", label: "Contém" },
  { value: "expressao", label: "Expressão" },
  { value: "regex_segura", label: "Regex segura" },
  { value: "semantico", label: "Semântico" },
]

function emptyForm(): TermoFormData {
  return {
    criterio: "",
    termo: "",
    descricao: "",
    tipo_correspondencia: "contem",
    intensidade_base: "",
    exige_contexto: false,
    regra_critica: false,
    considerar_mensagem_atual: true,
    considerar_historico: false,
    considerar_anexos: false,
    considerar_imagens: false,
    ativo: true,
  }
}

interface TermoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  termo: Termo | null
  criterios: Criterio[]
  intensidades: Intensidade[]
  onSave: () => void
}

export function TermoDialog({ open, onOpenChange, termo, criterios, intensidades, onSave }: TermoDialogProps) {
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState<TermoFormData>(emptyForm())

  useEffect(() => {
    if (termo) {
      setFormData({
        criterio: String(termo.criterio),
        termo: termo.termo,
        descricao: termo.descricao,
        tipo_correspondencia: termo.tipo_correspondencia,
        intensidade_base: String(termo.intensidade_base),
        exige_contexto: termo.exige_contexto,
        regra_critica: termo.regra_critica,
        considerar_mensagem_atual: termo.considerar_mensagem_atual,
        considerar_historico: termo.considerar_historico,
        considerar_anexos: termo.considerar_anexos,
        considerar_imagens: termo.considerar_imagens,
        ativo: termo.ativo,
      })
    } else {
      setFormData(emptyForm())
    }
  }, [termo, open])

  const intensidadesDoCriterio = intensidades.filter(
    (i) => formData.criterio && i.criterio === Number(formData.criterio)
  )

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.criterio) {
      toast.error("Selecione um critério")
      return
    }
    if (!formData.termo.trim()) {
      toast.error("Termo é obrigatório")
      return
    }
    if (!formData.intensidade_base) {
      toast.error("Selecione a intensidade base")
      return
    }

    const intensidadeSelecionada = intensidades.find((i) => i.id === Number(formData.intensidade_base))
    if (intensidadeSelecionada && intensidadeSelecionada.criterio !== Number(formData.criterio)) {
      toast.error("A intensidade base precisa pertencer ao mesmo critério do termo")
      return
    }

    setLoading(true)
    try {
      const payload = {
        ...formData,
        criterio: Number(formData.criterio),
        intensidade_base: Number(formData.intensidade_base),
      }
      const response = termo
        ? await ahpService.updateTermo(termo.id, payload)
        : await ahpService.createTermo(payload)

      if (response.success) {
        toast.success(termo ? "Termo atualizado com sucesso" : "Termo cadastrado com sucesso")
        onSave()
        onOpenChange(false)
      } else {
        toast.error(response.message || "Erro ao salvar termo")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{termo ? "Editar Termo" : "Novo Termo"}</DialogTitle>
          <DialogDescription>
            {termo ? "Atualize os dados do termo" : "Preencha os dados para cadastrar um novo termo"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="criterio">
                Critério <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.criterio}
                onValueChange={(value) => setFormData({ ...formData, criterio: value, intensidade_base: "" })}
              >
                <SelectTrigger id="criterio">
                  <SelectValue placeholder="Selecione" />
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
              <Label htmlFor="termo">
                Termo <span className="text-destructive">*</span>
              </Label>
              <Input
                id="termo"
                value={formData.termo}
                onChange={(e) => setFormData({ ...formData, termo: e.target.value })}
                required
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
              <Label htmlFor="tipo_correspondencia">Tipo de correspondência</Label>
              <Select
                value={formData.tipo_correspondencia}
                onValueChange={(value) =>
                  setFormData({ ...formData, tipo_correspondencia: value as TipoCorrespondencia })
                }
              >
                <SelectTrigger id="tipo_correspondencia">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPOS.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="intensidade_base">
                Intensidade base <span className="text-destructive">*</span>
              </Label>
              <Select
                value={formData.intensidade_base}
                onValueChange={(value) => setFormData({ ...formData, intensidade_base: value })}
              >
                <SelectTrigger id="intensidade_base">
                  <SelectValue placeholder="Selecione" />
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
                <Label htmlFor="exige_contexto" className="cursor-pointer">Exige contexto</Label>
                <Switch
                  id="exige_contexto"
                  checked={formData.exige_contexto}
                  onCheckedChange={(checked) => setFormData({ ...formData, exige_contexto: checked })}
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
                <Label htmlFor="considerar_mensagem_atual" className="cursor-pointer">Considerar mensagem atual</Label>
                <Switch
                  id="considerar_mensagem_atual"
                  checked={formData.considerar_mensagem_atual}
                  onCheckedChange={(checked) => setFormData({ ...formData, considerar_mensagem_atual: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="considerar_historico" className="cursor-pointer">Considerar histórico</Label>
                <Switch
                  id="considerar_historico"
                  checked={formData.considerar_historico}
                  onCheckedChange={(checked) => setFormData({ ...formData, considerar_historico: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="considerar_anexos" className="cursor-pointer">Considerar anexos</Label>
                <Switch
                  id="considerar_anexos"
                  checked={formData.considerar_anexos}
                  onCheckedChange={(checked) => setFormData({ ...formData, considerar_anexos: checked })}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="considerar_imagens" className="cursor-pointer">Considerar imagens</Label>
                <Switch
                  id="considerar_imagens"
                  checked={formData.considerar_imagens}
                  onCheckedChange={(checked) => setFormData({ ...formData, considerar_imagens: checked })}
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Salvando..." : termo ? "Atualizar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
