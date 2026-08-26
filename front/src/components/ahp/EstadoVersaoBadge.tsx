import { Badge } from "@/components/ui/badge"
import type { EstadoVersaoAHP } from "@/types/ahp"

const LABELS: Record<EstadoVersaoAHP, string> = {
  pendente_configuracao: "Pendente de configuração",
  rascunho: "Rascunho",
  processando: "Processando",
  valida: "Válida",
  inconsistente: "Inconsistente",
  ativa: "Ativa",
  arquivada: "Arquivada",
  erro: "Erro",
}

const VARIANTS: Record<EstadoVersaoAHP, "default" | "secondary" | "destructive" | "outline"> = {
  pendente_configuracao: "outline",
  rascunho: "secondary",
  processando: "secondary",
  valida: "default",
  inconsistente: "destructive",
  ativa: "default",
  arquivada: "outline",
  erro: "destructive",
}

export function EstadoVersaoBadge({ estado }: { estado: EstadoVersaoAHP }) {
  return <Badge variant={VARIANTS[estado] ?? "outline"}>{LABELS[estado] ?? estado}</Badge>
}
