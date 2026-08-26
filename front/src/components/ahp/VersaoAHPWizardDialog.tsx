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
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Loader2, CheckCircle2, XCircle } from "lucide-react"
import { toast } from "sonner"
import { ahpService } from "@/services/ahp.service"
import { ComparacaoMatrixForm, type ComparacaoMatrixItem } from "@/components/ahp/ComparacaoMatrixForm"
import type { ComparacaoPar, Criterio, VersaoAHP } from "@/types/ahp"

type VersaoPhase =
  | "descricao"
  | "comparacoes_criterios"
  | "comparacoes_intensidades"
  | "validando"
  | "validacao_resultado"
  | "ativando"
  | "ativacao_resultado"

interface VersaoAHPWizardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  resumeVersao: VersaoAHP | null
  onSave: () => void
}

export function VersaoAHPWizardDialog({ open, onOpenChange, resumeVersao, onSave }: VersaoAHPWizardDialogProps) {
  const [phase, setPhase] = useState<VersaoPhase>("descricao")
  const [descricao, setDescricao] = useState("")
  const [versaoId, setVersaoId] = useState<number | null>(null)
  const [criterios, setCriterios] = useState<Criterio[]>([])
  const [intensidadeIndex, setIntensidadeIndex] = useState(0)
  const [intensidadeItems, setIntensidadeItems] = useState<ComparacaoMatrixItem[]>([])
  const [loadingIntensidades, setLoadingIntensidades] = useState(false)
  const [validacaoErros, setValidacaoErros] = useState<string[]>([])
  const [ativacaoSucesso, setAtivacaoSucesso] = useState(false)
  const [ativacaoErros, setAtivacaoErros] = useState<{ estado: string | null; mensagens: string[] }>({
    estado: null,
    mensagens: [],
  })

  useEffect(() => {
    if (!open) return

    const bootstrap = async () => {
      const todosCriterios = await ahpService.listCriterios()
      const ativos = todosCriterios.filter((c) => c.ativo)
      setCriterios(ativos)

      if (resumeVersao) {
        setVersaoId(resumeVersao.id)
        setDescricao(resumeVersao.descricao)
        setPhase("comparacoes_criterios")
      } else {
        setVersaoId(null)
        setDescricao("")
        setPhase("descricao")
      }
      setIntensidadeIndex(0)
      setValidacaoErros([])
      setAtivacaoSucesso(false)
      setAtivacaoErros({ estado: null, mensagens: [] })
    }

    bootstrap().catch(() => toast.error("Erro ao carregar critérios"))
  }, [open, resumeVersao])

  useEffect(() => {
    if (phase !== "comparacoes_intensidades") return
    const criterio = criterios[intensidadeIndex]
    if (!criterio) return

    setLoadingIntensidades(true)
    ahpService
      .listIntensidades(criterio.id)
      .then((lista) => {
        const comparaveis = lista.filter(
          (i) => i.ativo && i.codigo !== "ausente" && i.codigo !== "inconclusiva"
        )
        setIntensidadeItems(comparaveis.map((i) => ({ id: i.id, label: i.nome })))
      })
      .finally(() => setLoadingIntensidades(false))
  }, [phase, intensidadeIndex, criterios])

  useEffect(() => {
    if (phase !== "validando" || !versaoId) return
    ahpService.validarVersao(versaoId).then((resultado) => {
      setValidacaoErros(resultado.erros)
      setPhase("validacao_resultado")
    })
  }, [phase, versaoId])

  useEffect(() => {
    if (phase !== "ativando" || !versaoId) return
    ahpService.ativarVersao(versaoId).then((resultado) => {
      if (resultado.success) {
        setAtivacaoSucesso(true)
      } else {
        setAtivacaoSucesso(false)
        setAtivacaoErros({ estado: resultado.estado, mensagens: resultado.mensagens_erro })
      }
      setPhase("ativacao_resultado")
    })
  }, [phase, versaoId])

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen && (phase === "validando" || phase === "ativando")) return
    onOpenChange(nextOpen)
  }

  const handleCriarRascunho = async () => {
    const response = await ahpService.createVersao(descricao)
    if (response.success && response.data) {
      setVersaoId(response.data.id)
      setPhase("comparacoes_criterios")
    } else {
      toast.error(response.message || "Erro ao criar versão")
    }
  }

  const handleSubmitCriterios = async (pares: ComparacaoPar[]) => {
    if (!versaoId) return
    const response = await ahpService.submitComparacoesCriterios(versaoId, pares)
    if (response.success) {
      setPhase("comparacoes_intensidades")
      setIntensidadeIndex(0)
    } else {
      toast.error(response.message || "Erro ao salvar comparações de critérios")
    }
  }

  const handleSubmitIntensidades = async (pares: ComparacaoPar[]) => {
    if (!versaoId) return
    const criterio = criterios[intensidadeIndex]
    if (!criterio) return

    const response = await ahpService.submitComparacoesIntensidades(versaoId, criterio.codigo, pares)
    if (!response.success) {
      toast.error(response.message || "Erro ao salvar comparações de intensidades")
      return
    }

    if (intensidadeIndex + 1 < criterios.length) {
      setIntensidadeIndex((prev) => prev + 1)
    } else {
      setPhase("validando")
    }
  }

  const handleFechar = () => {
    onOpenChange(false)
    onSave()
  }

  const renderContent = () => {
    switch (phase) {
      case "descricao":
        return (
          <>
            <DialogHeader>
              <DialogTitle>Nova Versão AHP</DialogTitle>
              <DialogDescription>Descreva o propósito desta versão antes de iniciar as comparações.</DialogDescription>
            </DialogHeader>
            <div className="space-y-2 py-4">
              <Label htmlFor="descricao">Descrição</Label>
              <Textarea
                id="descricao"
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                rows={3}
                placeholder="Ex: Ajuste de pesos após revisão trimestral"
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancelar</Button>
              <Button onClick={handleCriarRascunho}>Criar rascunho</Button>
            </DialogFooter>
          </>
        )

      case "comparacoes_criterios":
        return (
          <>
            <DialogHeader>
              <DialogTitle>Comparação entre Critérios</DialogTitle>
              <DialogDescription>
                Indique a importância relativa de cada par de critérios.
              </DialogDescription>
            </DialogHeader>
            <ComparacaoMatrixForm
              items={criterios.map((c) => ({ id: c.id, label: c.nome }))}
              title="Comparação entre critérios"
              submitLabel="Salvar e continuar"
              onSubmit={handleSubmitCriterios}
            />
          </>
        )

      case "comparacoes_intensidades": {
        const criterio = criterios[intensidadeIndex]
        return (
          <>
            <DialogHeader>
              <DialogTitle>Comparação de Intensidades — {criterio?.nome}</DialogTitle>
              <DialogDescription>
                Critério {intensidadeIndex + 1} de {criterios.length}
              </DialogDescription>
            </DialogHeader>
            {loadingIntensidades ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <ComparacaoMatrixForm
                items={intensidadeItems}
                title={`Comparação de intensidades: ${criterio?.nome ?? ""}`}
                submitLabel={intensidadeIndex + 1 < criterios.length ? "Salvar e ir para o próximo critério" : "Salvar e validar"}
                onSubmit={handleSubmitIntensidades}
              />
            )}
          </>
        )
      }

      case "validando":
        return (
          <>
            <DialogHeader>
              <DialogTitle>Validando versão...</DialogTitle>
              <DialogDescription>Verificando consistência das comparações informadas.</DialogDescription>
            </DialogHeader>
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          </>
        )

      case "validacao_resultado":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {validacaoErros.length === 0 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-destructive" />
                )}
                {validacaoErros.length === 0 ? "Versão válida" : "Foram encontrados problemas"}
              </DialogTitle>
            </DialogHeader>
            {validacaoErros.length > 0 && (
              <ul className="list-disc space-y-1 pl-5 text-sm text-destructive">
                {validacaoErros.map((erro, i) => (
                  <li key={i}>{erro}</li>
                ))}
              </ul>
            )}
            <DialogFooter>
              {validacaoErros.length === 0 ? (
                <Button onClick={() => setPhase("ativando")} className="w-full">Ativar versão</Button>
              ) : (
                <Button variant="outline" onClick={() => setPhase("comparacoes_criterios")} className="w-full">
                  Voltar e corrigir
                </Button>
              )}
            </DialogFooter>
          </>
        )

      case "ativando":
        return (
          <>
            <DialogHeader>
              <DialogTitle>Ativando versão...</DialogTitle>
            </DialogHeader>
            <div className="flex justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          </>
        )

      case "ativacao_resultado":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {ativacaoSucesso ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-destructive" />
                )}
                {ativacaoSucesso ? "Versão ativada" : "Não foi possível ativar"}
              </DialogTitle>
            </DialogHeader>
            {!ativacaoSucesso && (
              <div className="space-y-2">
                {ativacaoErros.estado && (
                  <p className="text-sm text-muted-foreground">Estado: {ativacaoErros.estado}</p>
                )}
                <ul className="list-disc space-y-1 pl-5 text-sm text-destructive">
                  {ativacaoErros.mensagens.map((erro, i) => (
                    <li key={i}>{erro}</li>
                  ))}
                </ul>
              </div>
            )}
            <DialogFooter>
              {ativacaoSucesso ? (
                <Button onClick={handleFechar} className="w-full">Fechar</Button>
              ) : (
                <Button variant="outline" onClick={() => setPhase("comparacoes_criterios")} className="w-full">
                  Voltar e corrigir
                </Button>
              )}
            </DialogFooter>
          </>
        )
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        className="max-w-2xl max-h-[85vh] overflow-y-auto"
        onInteractOutside={(e) => {
          if (phase === "validando" || phase === "ativando") e.preventDefault()
        }}
        onEscapeKeyDown={(e) => {
          if (phase === "validando" || phase === "ativando") e.preventDefault()
        }}
      >
        {renderContent()}
      </DialogContent>
    </Dialog>
  )
}
