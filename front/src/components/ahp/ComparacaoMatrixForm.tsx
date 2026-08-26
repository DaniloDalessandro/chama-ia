"use client"

import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import type { ComparacaoPar } from "@/types/ahp"

export interface ComparacaoMatrixItem {
  id: number
  label: string
}

interface ComparacaoMatrixFormProps {
  items: ComparacaoMatrixItem[]
  title: string
  onSubmit: (pares: ComparacaoPar[]) => Promise<void>
  submitLabel: string
}

/**
 * Escala Saaty nomeada em termos de negócio (9 valores primários). Os
 * valores intermediários pares (2/4/6/8) e seus recíprocos ficam fora de
 * escopo desta rodada.
 */
function saatyOptions(labelA: string, labelB: string) {
  return [
    { value: 9, text: `9 — Extrema importância de "${labelA}" sobre "${labelB}"` },
    { value: 7, text: `7 — Muito forte importância de "${labelA}" sobre "${labelB}"` },
    { value: 5, text: `5 — Forte importância de "${labelA}" sobre "${labelB}"` },
    { value: 3, text: `3 — Importância moderada de "${labelA}" sobre "${labelB}"` },
    { value: 1, text: "1 — Igual importância" },
    { value: 1 / 3, text: `1/3 — Importância moderada de "${labelB}" sobre "${labelA}"` },
    { value: 1 / 5, text: `1/5 — Forte importância de "${labelB}" sobre "${labelA}"` },
    { value: 1 / 7, text: `1/7 — Muito forte importância de "${labelB}" sobre "${labelA}"` },
    { value: 1 / 9, text: `1/9 — Extrema importância de "${labelB}" sobre "${labelA}"` },
  ]
}

export function ComparacaoMatrixForm({ items, title, onSubmit, submitLabel }: ComparacaoMatrixFormProps) {
  const pairs = useMemo(() => {
    const result: { a: ComparacaoMatrixItem; b: ComparacaoMatrixItem }[] = []
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        result.push({ a: items[i], b: items[j] })
      }
    }
    return result
  }, [items])

  const [valores, setValores] = useState<Record<string, number | undefined>>({})
  const [submitting, setSubmitting] = useState(false)

  const pairKey = (a: ComparacaoMatrixItem, b: ComparacaoMatrixItem) => `${a.id}-${b.id}`

  const handleSubmit = async () => {
    const faltando = pairs.some((p) => valores[pairKey(p.a, p.b)] === undefined)
    if (faltando) {
      toast.error("Preencha todas as comparações antes de continuar")
      return
    }

    const paresPayload: ComparacaoPar[] = pairs.map((p) => ({
      item_linha_id: p.a.id,
      item_coluna_id: p.b.id,
      valor_saaty: valores[pairKey(p.a, p.b)] as number,
    }))

    setSubmitting(true)
    try {
      await onSubmit(paresPayload)
    } finally {
      setSubmitting(false)
    }
  }

  if (items.length < 2) {
    return (
      <p className="text-sm text-muted-foreground">
        É necessário ao menos 2 itens ativos para gerar comparações.
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium">{title}</p>
      <div className="space-y-3 max-h-[50vh] overflow-y-auto pr-1">
        {pairs.map((p) => {
          const key = pairKey(p.a, p.b)
          const options = saatyOptions(p.a.label, p.b.label)
          return (
            <div key={key} className="rounded-lg border p-3 space-y-2">
              <p className="text-sm">
                <span className="font-medium">{p.a.label}</span> vs{" "}
                <span className="font-medium">{p.b.label}</span>
              </p>
              <Select
                value={valores[key] !== undefined ? String(valores[key]) : ""}
                onValueChange={(value) => setValores((prev) => ({ ...prev, [key]: Number(value) }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a importância relativa" />
                </SelectTrigger>
                <SelectContent>
                  {options.map((opt) => (
                    <SelectItem key={opt.value} value={String(opt.value)}>
                      {opt.text}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )
        })}
      </div>
      <Button onClick={handleSubmit} disabled={submitting} className="w-full">
        {submitting ? "Enviando..." : submitLabel}
      </Button>
    </div>
  )
}
