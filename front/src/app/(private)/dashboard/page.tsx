"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Ticket,
  MessagesSquare,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Users,
  Brain,
  TrendingUp,
} from "lucide-react"
import { chamadoAdminService } from "@/services/chamado-admin.service"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import clienteService from "@/services/clienteService"
import type { AtendimentoFilaCard } from "@/types/atendimento"

interface EstatisticasChamados {
  total: number
  abertos: number
  em_atendimento: number
  resolvidos_hoje: number
  criados_hoje: number
  criados_semana: number
  criados_mes: number
  por_status: { status: string; count: number }[]
  por_prioridade: { prioridade: string; count: number }[]
  por_tipo: { tipo: string; count: number }[]
}

const prioridadeConfig: Record<string, { label: string; color: string }> = {
  p1: { label: "P1 – Crítica", color: "bg-red-100 text-red-700 border-red-200" },
  p2: { label: "P2 – Alta", color: "bg-orange-100 text-orange-700 border-orange-200" },
  p3: { label: "P3 – Média", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  p4: { label: "P4 – Baixa", color: "bg-green-100 text-green-700 border-green-200" },
  urgente: { label: "Urgente", color: "bg-red-100 text-red-700 border-red-200" },
  alta: { label: "Alta", color: "bg-orange-100 text-orange-700 border-orange-200" },
  media: { label: "Média", color: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  baixa: { label: "Baixa", color: "bg-green-100 text-green-700 border-green-200" },
  revisao_humana: { label: "Revisão Humana", color: "bg-purple-100 text-purple-700 border-purple-200" },
  nao_classificado: { label: "Não Classificado", color: "bg-gray-100 text-gray-600 border-gray-200" },
}

const statusAtendimentoConfig: Record<string, { label: string; color: string }> = {
  aguardando: { label: "Aguardando", color: "bg-yellow-100 text-yellow-700" },
  em_atendimento: { label: "Em Atendimento", color: "bg-blue-100 text-blue-700" },
  aguardando_cliente: { label: "Ag. Cliente", color: "bg-orange-100 text-orange-700" },
  resolvido: { label: "Resolvido", color: "bg-green-100 text-green-700" },
  cancelado: { label: "Cancelado", color: "bg-gray-100 text-gray-600" },
  encaminhado_para_chamado: { label: "Encaminhado", color: "bg-purple-100 text-purple-700" },
}

function PrioridadeBadge({ prioridade }: { prioridade: string }) {
  const cfg = prioridadeConfig[prioridade] ?? { label: prioridade, color: "bg-gray-100 text-gray-600 border-gray-200" }
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  loading,
}: {
  title: string
  value: number | string
  subtitle: string
  icon: React.ElementType
  loading: boolean
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="h-8 w-16 animate-pulse rounded bg-muted" />
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      </CardContent>
    </Card>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState<EstatisticasChamados | null>(null)
  const [fila, setFila] = useState<AtendimentoFilaCard[]>([])
  const [totalClientes, setTotalClientes] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [estatisticas, filaData, clientes] = await Promise.allSettled([
          chamadoAdminService.getEstatisticas(),
          atendimentoAdminService.getFila(),
          clienteService.list(),
        ])

        if (estatisticas.status === "fulfilled") setStats(estatisticas.value)
        if (filaData.status === "fulfilled") setFila(filaData.value)
        if (clientes.status === "fulfilled") setTotalClientes(clientes.value.length)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const filaAtiva = fila.filter(
    (a) => a.status_atendimento === "aguardando" || a.status_atendimento === "em_atendimento"
  )
  const filaP1P2 = filaAtiva.filter((a) => a.prioridade === "p1" || a.prioridade === "p2")
  const atendimentosComAHP = fila.filter((a) => a.indice_ahp !== null).length

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Bem-vindo de volta{user?.name ? `, ${user.name}` : ""}!
        </p>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Chamados Abertos"
          value={stats?.abertos ?? "—"}
          subtitle={`${stats?.em_atendimento ?? 0} em atendimento`}
          icon={Ticket}
          loading={loading}
        />
        <KpiCard
          title="Criados Hoje"
          value={stats?.criados_hoje ?? "—"}
          subtitle={`${stats?.criados_semana ?? 0} nesta semana`}
          icon={TrendingUp}
          loading={loading}
        />
        <KpiCard
          title="Resolvidos Hoje"
          value={stats?.resolvidos_hoje ?? "—"}
          subtitle={`${stats?.criados_mes ?? 0} chamados no mês`}
          icon={CheckCircle2}
          loading={loading}
        />
        <KpiCard
          title="Atendimentos na Fila"
          value={filaAtiva.length}
          subtitle={`${filaP1P2.length} com prioridade P1/P2`}
          icon={MessagesSquare}
          loading={loading}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Distribuição por Prioridade */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4" />
              Prioridade dos Chamados
            </CardTitle>
            <CardDescription>Distribuição atual por banda AHP</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-5 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : stats?.por_prioridade?.length ? (
              <div className="space-y-3">
                {stats.por_prioridade.map(({ prioridade, count }) => {
                  const total = stats.por_prioridade.reduce((s, p) => s + p.count, 0)
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  const cfg = prioridadeConfig[prioridade] ?? {
                    label: prioridade,
                    color: "bg-gray-100 text-gray-600 border-gray-200",
                  }
                  return (
                    <div key={prioridade} className="flex items-center gap-3">
                      <div className="w-28 shrink-0">
                        <PrioridadeBadge prioridade={prioridade} />
                      </div>
                      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-foreground/20"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8 text-right">{count}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum dado disponível.</p>
            )}
          </CardContent>
        </Card>

        {/* Distribuição por Status Kanban */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Ticket className="h-4 w-4" />
              Status Kanban
            </CardTitle>
            <CardDescription>Posição dos chamados no quadro</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : stats?.por_status?.length ? (
              <div className="space-y-3">
                {stats.por_status.map(({ status, count }) => {
                  const labels: Record<string, string> = {
                    novo: "Novo",
                    em_andamento: "Em Andamento",
                    concluido: "Concluído",
                    aberto: "Aberto",
                    em_atendimento: "Em Atendimento",
                    resolvido: "Resolvido",
                    fechado: "Fechado",
                    cancelado: "Cancelado",
                  }
                  const total = stats.por_status.reduce((s, p) => s + p.count, 0)
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{labels[status] ?? status}</span>
                        <span className="font-medium">{count}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-foreground/30"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum dado disponível.</p>
            )}
          </CardContent>
        </Card>

        {/* Indicadores IA / AHP */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" />
              Inteligência Artificial
            </CardTitle>
            <CardDescription>Métricas do pipeline AHP</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Atendimentos classificados</span>
                {loading ? (
                  <div className="h-4 w-10 animate-pulse rounded bg-muted" />
                ) : (
                  <span className="text-sm font-semibold">{atendimentosComAHP}</span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total na fila (chat)</span>
                {loading ? (
                  <div className="h-4 w-10 animate-pulse rounded bg-muted" />
                ) : (
                  <span className="text-sm font-semibold">{fila.length}</span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Revisão humana pendente</span>
                {loading ? (
                  <div className="h-4 w-10 animate-pulse rounded bg-muted" />
                ) : (
                  <span className="text-sm font-semibold">
                    {fila.filter((a) => a.prioridade === "revisao_humana").length}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Regra crítica ativada</span>
                {loading ? (
                  <div className="h-4 w-10 animate-pulse rounded bg-muted" />
                ) : (
                  <span className="text-sm font-semibold">
                    {fila.filter((a) => a.regra_critica_confirmada).length}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Clientes cadastrados</span>
                {loading ? (
                  <div className="h-4 w-10 animate-pulse rounded bg-muted" />
                ) : (
                  <span className="text-sm font-semibold">{totalClientes ?? "—"}</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Fila de Atendimentos */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" />
              Fila de Atendimentos
            </CardTitle>
            <CardDescription>
              {filaAtiva.length} {filaAtiva.length === 1 ? "atendimento ativo" : "atendimentos ativos"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-14 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : filaAtiva.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum atendimento na fila.</p>
            ) : (
              <div className="space-y-3">
                {filaAtiva.slice(0, 5).map((a) => {
                  const statusCfg = statusAtendimentoConfig[a.status_atendimento] ?? {
                    label: a.status_atendimento,
                    color: "bg-gray-100 text-gray-600",
                  }
                  return (
                    <div key={a.id} className="flex items-start justify-between gap-2 rounded-md border p-2.5">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{a.nome || "Sem nome"}</p>
                        <p className="truncate text-xs text-muted-foreground">{a.assunto || "Sem assunto"}</p>
                        <div className="mt-1 flex items-center gap-2">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusCfg.color}`}>
                            {statusCfg.label}
                          </span>
                          {a.tempo_espera_minutos != null && (
                            <span className="text-xs text-muted-foreground">
                              {a.tempo_espera_minutos}min
                            </span>
                          )}
                        </div>
                      </div>
                      <PrioridadeBadge prioridade={a.prioridade} />
                    </div>
                  )
                })}
                {filaAtiva.length > 5 && (
                  <p className="text-center text-xs text-muted-foreground">
                    +{filaAtiva.length - 5} outros
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Chamados por Tipo */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-4 w-4" />
              Chamados por Tipo
            </CardTitle>
            <CardDescription>Distribuição por categoria de chamado</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-8 animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : stats?.por_tipo?.length ? (
              <div className="space-y-3">
                {stats.por_tipo.map(({ tipo, count }) => {
                  const total = stats.por_tipo.reduce((s, p) => s + p.count, 0)
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0
                  return (
                    <div key={tipo} className="flex items-center gap-3">
                      <span className="w-36 shrink-0 truncate text-sm text-muted-foreground capitalize">
                        {tipo.replace(/_/g, " ")}
                      </span>
                      <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-foreground/25"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8 text-right">{count}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Nenhum dado disponível.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
