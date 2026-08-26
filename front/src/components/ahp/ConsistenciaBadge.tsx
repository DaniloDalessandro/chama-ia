import { CheckCircle2, HelpCircle, XCircle } from "lucide-react"
import type { EstadoVersaoAHP } from "@/types/ahp"

interface ConsistenciaBadgeProps {
  estado: EstadoVersaoAHP
}

/**
 * Deriva "Consistente/Inconsistente/Pendente" exclusivamente de `estado` --
 * nunca recebe CR numérico como prop, então é impossível vazar o número
 * bruto de consistência AHP para a UI (nem para staff).
 */
export function ConsistenciaBadge({ estado }: ConsistenciaBadgeProps) {
  if (estado === "valida" || estado === "ativa") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600 dark:text-green-400">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        Consistente
      </span>
    )
  }

  if (estado === "inconsistente") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-destructive">
        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
        Inconsistente
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
      <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
      —
    </span>
  )
}
