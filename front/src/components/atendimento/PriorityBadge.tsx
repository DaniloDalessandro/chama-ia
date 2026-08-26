import { AlertCircle, AlertOctagon, AlertTriangle, CheckCircle2, HelpCircle, UserCheck } from "lucide-react"
import type { Prioridade } from "@/types/atendimento"

interface PriorityBadgeConfig {
  label: string
  hex: string
  icon: typeof AlertOctagon
}

const CONFIG: Record<Prioridade, PriorityBadgeConfig> = {
  p1: { label: "P1 · Crítico", hex: "#DC2626", icon: AlertOctagon },
  p2: { label: "P2 · Alto", hex: "#EA580C", icon: AlertTriangle },
  p3: { label: "P3 · Médio", hex: "#CA8A04", icon: AlertCircle },
  p4: { label: "P4 · Baixo", hex: "#16A34A", icon: CheckCircle2 },
  nao_classificado: { label: "Não classificado", hex: "#64748B", icon: HelpCircle },
  revisao_humana: { label: "Revisão humana", hex: "#7C3AED", icon: UserCheck },
}

interface PriorityBadgeProps {
  prioridade: Prioridade
  className?: string
}

/**
 * Nunca usa apenas cor -- sempre ícone + rótulo textual visível, conforme
 * a regra de acessibilidade do spec (seção 18).
 */
export function PriorityBadge({ prioridade, className }: PriorityBadgeProps) {
  const config = CONFIG[prioridade] ?? CONFIG.nao_classificado
  const Icon = config.icon

  return (
    <span
      title={config.label}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${className ?? ""}`}
      style={{
        backgroundColor: `${config.hex}1a`,
        color: config.hex,
        borderColor: `${config.hex}40`,
      }}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {config.label}
    </span>
  )
}
