"use client"

import { useCallback, useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  Mail,
  Phone,
  Paperclip,
  RefreshCw,
  ScrollText,
  ShieldAlert,
  User,
} from "lucide-react"
import { DetailsSkeleton } from "@/components/common/LoadingSkeletons"
import { PriorityBadge } from "@/components/atendimento/PriorityBadge"
import { ConversaThread } from "@/components/atendimento/ConversaThread"
import { MessageComposer } from "@/components/atendimento/MessageComposer"
import { AuditoriaSummaryCard } from "@/components/atendimento/AuditoriaSummaryCard"
import { ClassificarDialog } from "@/components/atendimento/ClassificarDialog"
import { RevisaoHumanaDialog } from "@/components/atendimento/RevisaoHumanaDialog"
import { EncaminharChamadoDialog } from "@/components/atendimento/EncaminharChamadoDialog"
import { atendimentoAdminService } from "@/services/atendimento-admin.service"
import { useAtendimentoChat } from "@/hooks/useAtendimentoChat"
import type { AtendimentoDetalhe } from "@/types/atendimento"

function formatTempoEspera(totalMinutes: number) {
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = Math.floor(totalMinutes % 60)
  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  parts.push(`${minutes}min`)
  return parts.join(" ")
}

export default function AtendimentoDetailPage() {
  const params = useParams()
  const router = useRouter()
  const rawId = params?.id
  const atendimentoId = rawId ? Number(Array.isArray(rawId) ? rawId[0] : rawId) : 0

  const [detalhe, setDetalhe] = useState<AtendimentoDetalhe | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isClassificarOpen, setIsClassificarOpen] = useState(false)
  const [isRevisaoOpen, setIsRevisaoOpen] = useState(false)
  const [isEncaminharOpen, setIsEncaminharOpen] = useState(false)

  const fetchDetalhe = useCallback(async () => {
    if (!atendimentoId) return
    try {
      const data = await atendimentoAdminService.getDetalhe(atendimentoId)
      setDetalhe(data)
    } catch (error) {
      console.error("Erro ao carregar atendimento:", error)
      toast.error("Erro ao carregar atendimento")
    } finally {
      setIsLoading(false)
    }
  }, [atendimentoId])

  useEffect(() => {
    fetchDetalhe()
  }, [fetchDetalhe])

  const { isConnected, messages, sendMessage, sendTyping } = useAtendimentoChat({
    atendimentoId: detalhe ? atendimentoId : null,
    mode: "staff",
    initialMessages: detalhe?.conversa,
  })

  if (isLoading) {
    return (
      <div className="p-6">
        <DetailsSkeleton />
      </div>
    )
  }

  if (!detalhe) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <p className="text-lg text-muted-foreground">Atendimento não encontrado</p>
        <div className="flex gap-3">
          <Button onClick={() => router.push("/atendimentos")} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar
          </Button>
          <Button onClick={fetchDetalhe}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  const { atendimento } = detalhe

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Button onClick={() => router.push("/atendimentos")} variant="ghost" size="icon">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold">{atendimento.nome}</h1>
            <PriorityBadge prioridade={atendimento.prioridade} />
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Mail className="h-3.5 w-3.5" />
              {atendimento.email}
            </span>
            {atendimento.telefone && (
              <span className="inline-flex items-center gap-1">
                <Phone className="h-3.5 w-3.5" />
                {atendimento.telefone}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <User className="h-3.5 w-3.5" />
              Origem: {atendimento.origem === "chat" ? "Chat" : "E-mail"}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Conversa</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ConversaThread mensagens={messages} />
              <MessageComposer isConnected={isConnected} onSend={sendMessage} onTyping={sendTyping} />
            </CardContent>
          </Card>

          <AuditoriaSummaryCard
            atendimentoId={atendimento.id}
            assunto={atendimento.assunto}
            resumo={atendimento.resumo}
            servicoAfetado={atendimento.servico_afetado}
            indiceAhp={atendimento.indice_ahp}
            avaliacoes={detalhe.avaliacoes_criterios}
            auditoriaMaisRecente={detalhe.auditoria_mais_recente}
            onSaved={fetchDetalhe}
          />

          {detalhe.regra_critica && (
            <Card className="border-red-300 dark:border-red-800">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-red-700 dark:text-red-400">
                  <ShieldAlert className="h-5 w-5" />
                  Regra crítica
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">
                  {detalhe.regra_critica.confirmada
                    ? "Regra crítica confirmada para este atendimento."
                    : "Regra crítica avaliada, mas não confirmada."}
                </p>
                {detalhe.regra_critica.justificativa && (
                  <p className="mt-1 text-sm text-muted-foreground">{detalhe.regra_critica.justificativa}</p>
                )}
              </CardContent>
            </Card>
          )}

          {detalhe.revisoes_humanas.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Histórico de revisões humanas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {detalhe.revisoes_humanas.map((revisao) => (
                  <div key={revisao.id} className="rounded-lg border p-3 text-sm">
                    <p className="font-medium">
                      {revisao.prioridade_anterior} → {revisao.nova_prioridade}
                    </p>
                    <p className="mt-1 text-muted-foreground">{revisao.justificativa}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(revisao.criado_em).toLocaleString("pt-BR")}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {detalhe.anexos.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Paperclip className="h-5 w-5" />
                  Anexos ({detalhe.anexos.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {detalhe.anexos.map((anexo) => (
                  <a
                    key={anexo.id}
                    href={anexo.arquivo}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted transition-colors"
                  >
                    <ScrollText className="h-6 w-6 text-muted-foreground" />
                    <div className="flex-1 min-w-0">
                      <p className="truncate font-medium">{anexo.nome_original}</p>
                      <p className="text-xs text-muted-foreground">{(anexo.tamanho / 1024).toFixed(1)} KB</p>
                    </div>
                  </a>
                ))}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Ações</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full" onClick={() => setIsClassificarOpen(true)}>
                Classificar com IA
              </Button>
              <Button variant="outline" className="w-full" onClick={() => setIsRevisaoOpen(true)}>
                Revisão humana
              </Button>
              <Button variant="outline" className="w-full" onClick={() => setIsEncaminharOpen(true)}>
                Encaminhar para chamado
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Informações</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground">Tempo aguardando</p>
                <p className="font-medium">
                  {formatTempoEspera(
                    Math.floor((Date.now() - new Date(atendimento.criado_em).getTime()) / 60000)
                  )}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Anexos</p>
                <p className="font-medium">{detalhe.anexos.length}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Token de sessão</p>
                <p className="break-all font-mono text-xs">{atendimento.session_token}</p>
              </div>
            </CardContent>
          </Card>

          {detalhe.chamado_relacionado && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Chamado relacionado</CardTitle>
              </CardHeader>
              <CardContent>
                <button
                  type="button"
                  className="text-left text-primary hover:underline"
                  onClick={() => router.push(`/chamados/${detalhe.chamado_relacionado?.id}`)}
                >
                  #{detalhe.chamado_relacionado.protocolo} — {detalhe.chamado_relacionado.status_display}
                </button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      <ClassificarDialog
        open={isClassificarOpen}
        onOpenChange={setIsClassificarOpen}
        atendimentoId={atendimento.id}
        onSuccess={fetchDetalhe}
      />
      <RevisaoHumanaDialog
        open={isRevisaoOpen}
        onOpenChange={setIsRevisaoOpen}
        atendimentoId={atendimento.id}
        onSuccess={fetchDetalhe}
      />
      <EncaminharChamadoDialog
        open={isEncaminharOpen}
        onOpenChange={setIsEncaminharOpen}
        atendimentoId={atendimento.id}
        onSuccess={fetchDetalhe}
      />
    </div>
  )
}
