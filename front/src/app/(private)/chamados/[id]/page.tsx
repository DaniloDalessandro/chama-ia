"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/components/ui/sonner"
import {
  ArrowLeft,
  User,
  Mail,
  Phone,
  Calendar,
  Clock,
  FileText,
  AlertCircle,
  DollarSign,
  HelpCircle,
  Paperclip,
  MessageSquare,
  Send,
  Loader2,
  ExternalLink,
  Lock,
  RefreshCw,
  Globe,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  chamadoAdminService,
  type ChamadoDetail,
} from "@/services/chamado-admin.service"

const tipoIcons: Record<string, typeof FileText> = {
  "nota-fiscal": FileText,
  "erro-sistema": AlertCircle,
  financeiro: DollarSign,
  outros: HelpCircle,
}

const prioridadeColors: Record<string, string> = {
  baixa: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  media: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  alta: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  urgente: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
}

const statusKanbanColors: Record<string, string> = {
  novo: "bg-blue-500",
  em_andamento: "bg-yellow-500",
  concluido: "bg-green-500",
}

function formatDateTime(dateString: string) {
  return new Date(dateString).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatTempoAberto(createdAt: string) {
  const diffMs = Date.now() - new Date(createdAt).getTime()
  const totalMinutes = Math.floor(diffMs / 60000)
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = totalMinutes % 60

  const parts: string[] = []
  if (days > 0) parts.push(`${days}d`)
  if (hours > 0) parts.push(`${hours}h`)
  parts.push(`${minutes}min`)
  return parts.join(" ")
}

export default function ChamadoDetailPage() {
  const params = useParams()
  const router = useRouter()
  const rawId = params?.id
  const chamadoId = rawId ? Number(Array.isArray(rawId) ? rawId[0] : rawId) : 0

  const [chamado, setChamado] = useState<ChamadoDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [newComment, setNewComment] = useState("")
  const [commentType] = useState<"publico" | "interno">("interno")
  const [isSendingComment, setIsSendingComment] = useState(false)
  const [selectedPrioridade, setSelectedPrioridade] = useState("")
  const [selectedStatusKanban, setSelectedStatusKanban] = useState("")

  const fetchChamado = useCallback(async () => {
    if (!chamadoId || chamadoId <= 0) return
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await chamadoAdminService.get(chamadoId)
      setChamado(data)
      setSelectedPrioridade(data.prioridade)
      setSelectedStatusKanban(data.status_kanban)
    } catch (err) {
      console.error("Erro ao carregar chamado:", err)
      const message = err instanceof Error ? err.message : "Erro ao carregar chamado"
      setLoadError(message)
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }, [chamadoId])

  useEffect(() => {
    fetchChamado()
  }, [fetchChamado])

  const handleSendComment = async () => {
    if (!chamado || !newComment.trim()) return

    setIsSendingComment(true)
    try {
      const response = await chamadoAdminService.addComentario(
        chamado.id,
        newComment,
        commentType
      )
      if (response.success) {
        toast.success("Resposta enviada!")
        setNewComment("")
        fetchChamado()
      } else {
        toast.error(response.message || "Erro ao enviar resposta")
      }
    } catch (err) {
      toast.error("Erro ao enviar resposta")
    } finally {
      setIsSendingComment(false)
    }
  }

  const handlePrioridadeChange = async (value: string) => {
    if (!chamado) return

    setSelectedPrioridade(value)
    try {
      const response = await chamadoAdminService.updatePrioridade(chamado.id, value)
      if (response.success) {
        toast.success("Prioridade atualizada!")
        fetchChamado()
      } else {
        toast.error(response.message || "Erro ao atualizar prioridade")
        setSelectedPrioridade(chamado.prioridade)
      }
    } catch (err) {
      toast.error("Erro ao atualizar prioridade")
      setSelectedPrioridade(chamado.prioridade)
    }
  }

  const handleStatusKanbanChange = async (value: string) => {
    if (!chamado) return

    setSelectedStatusKanban(value)
    try {
      const response = await chamadoAdminService.updateStatusKanban(
        chamado.id,
        value as "novo" | "em_andamento" | "concluido"
      )
      if (response.success) {
        toast.success("Status atualizado!")
        fetchChamado()
      } else {
        toast.error(response.message || "Erro ao atualizar status")
        setSelectedStatusKanban(chamado.status_kanban)
      }
    } catch (err) {
      toast.error("Erro ao atualizar status")
      setSelectedStatusKanban(chamado.status_kanban)
    }
  }


  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!chamado) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <p className="text-lg text-muted-foreground">
          {loadError || "Chamado nao encontrado"}
        </p>
        <div className="flex gap-3">
          <Button onClick={() => router.back()} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar
          </Button>
          <Button onClick={fetchChamado} variant="default">
            <RefreshCw className="mr-2 h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      </div>
    )
  }

  const TipoIcon = tipoIcons[chamado.tipo] || HelpCircle

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button onClick={() => router.push("/chamados")} variant="ghost" size="icon">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <div
              className={cn(
                "h-3 w-3 rounded-full",
                statusKanbanColors[chamado.status_kanban]
              )}
            />
            <h1 className="text-2xl font-bold">#{chamado.protocolo}</h1>
            <Badge variant="outline">{chamado.status_kanban_display}</Badge>
            <Badge
              variant="secondary"
              className={cn(prioridadeColors[chamado.prioridade])}
            >
              {chamado.prioridade_display}
            </Badge>
            <Badge variant="secondary" className="flex items-center gap-1">
              <TipoIcon className="h-3 w-3" />
              {chamado.tipo_display}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1">{chamado.assunto}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Coluna principal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Descricao */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Informacoes do Chamado</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Dados do solicitante e chamado */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-muted-foreground">Nome:</span>
                  <span className="font-medium">{chamado.nome}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-muted-foreground">Email:</span>
                  <a href={`mailto:${chamado.email}`} className="font-medium text-primary hover:underline">{chamado.email}</a>
                </div>
                {chamado.telefone && (
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-muted-foreground">Telefone:</span>
                    <span className="font-medium">{chamado.telefone}</span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-muted-foreground">Tipo:</span>
                  <span className="font-medium">{chamado.tipo_display}</span>
                </div>
                <div className="flex items-center gap-2">
                  <ExternalLink className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-muted-foreground">Origem:</span>
                  <span className="font-medium">{chamado.origem_display}</span>
                </div>
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="text-muted-foreground">Prioridade:</span>
                  <Badge variant="secondary" className={cn("text-xs", prioridadeColors[chamado.prioridade])}>
                    {chamado.prioridade_display}
                  </Badge>
                </div>
              </div>

              <Separator />

              {/* Assunto */}
              <div>
                <p className="text-sm text-muted-foreground mb-1">Assunto</p>
                <p className="font-medium">{chamado.assunto}</p>
              </div>

              <Separator />

              {/* Descricao */}
              <div>
                <p className="text-sm text-muted-foreground mb-1">Descricao</p>
                <p className="whitespace-pre-wrap leading-relaxed">{chamado.descricao}</p>
              </div>

              {/* Anexos */}
              {chamado.anexos && chamado.anexos.length > 0 && (
                <>
                  <Separator />
                  <div>
                    <p className="text-sm font-medium flex items-center gap-2 mb-3">
                      <Paperclip className="h-4 w-4" />
                      Anexos ({chamado.anexos.length})
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {chamado.anexos.map((anexo) => (
                        <a
                          key={anexo.id}
                          href={anexo.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted transition-colors"
                        >
                          <FileText className="h-8 w-8 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <p className="font-medium truncate">{anexo.nome_original}</p>
                            <p className="text-xs text-muted-foreground">
                              {(anexo.tamanho / 1024).toFixed(1)} KB
                            </p>
                          </div>
                          <ExternalLink className="h-4 w-4 text-muted-foreground" />
                        </a>
                      ))}
                    </div>
                  </div>
                </>
              )}

            </CardContent>
          </Card>

          {/* Resposta / Comentarios */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Respostas e Comentarios ({chamado.comentarios?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Campo de resposta interna */}
              <div className="space-y-3 rounded-lg border p-4 bg-muted/30">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Nota interna</span>
                </div>
                <Textarea
                  placeholder="Nota interna (apenas equipe)..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="resize-none bg-background"
                  rows={4}
                />
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    Apenas a equipe interna vera esta nota
                  </p>
                  <Button
                    onClick={handleSendComment}
                    disabled={!newComment.trim() || isSendingComment}
                  >
                    {isSendingComment ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="mr-2 h-4 w-4" />
                    )}
                    Enviar Nota
                  </Button>
                </div>
              </div>

              {/* Lista de comentarios */}
              {chamado.comentarios && chamado.comentarios.length > 0 && (
                <>
                  <Separator />
                  <div className="space-y-3">
                    {chamado.comentarios.map((comentario) => (
                      <div
                        key={comentario.id}
                        className={cn(
                          "rounded-lg p-4",
                          comentario.tipo === "interno"
                            ? "bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800"
                            : comentario.is_from_client
                            ? "bg-blue-50 dark:bg-blue-950/50 ml-8"
                            : "bg-muted mr-8"
                        )}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm">
                              {comentario.autor_nome || "Cliente"}
                            </span>
                            {comentario.tipo === "interno" && (
                              <Badge variant="outline" className="text-xs h-5 bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300 border-amber-300">
                                <Lock className="h-2.5 w-2.5 mr-1" />
                                Interno
                              </Badge>
                            )}
                            {comentario.tipo === "publico" && !comentario.is_from_client && (
                              <Badge variant="outline" className="text-xs h-5">
                                <Globe className="h-2.5 w-2.5 mr-1" />
                                Publico
                              </Badge>
                            )}
                            {comentario.is_from_client && (
                              <Badge variant="outline" className="text-xs h-5 bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-blue-300">
                                Cliente
                              </Badge>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatDateTime(comentario.created_at)}
                          </span>
                        </div>
                        <p className="whitespace-pre-wrap text-sm">{comentario.conteudo}</p>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {(!chamado.comentarios || chamado.comentarios.length === 0) && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Nenhuma resposta ou comentario ainda.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Detalhes / Acoes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Gerenciar</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Status</p>
                <Select value={selectedStatusKanban} onValueChange={handleStatusKanbanChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="novo">Novo</SelectItem>
                    <SelectItem value="em_andamento">Em Andamento</SelectItem>
                    <SelectItem value="concluido">Concluido</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-1">Prioridade</p>
                <Select value={selectedPrioridade} onValueChange={handlePrioridadeChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baixa">Baixa</SelectItem>
                    <SelectItem value="media">Media</SelectItem>
                    <SelectItem value="alta">Alta</SelectItem>
                    <SelectItem value="urgente">Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>

            </CardContent>
          </Card>

          {/* Datas */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Datas</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-3 text-sm">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-muted-foreground">Criado em</p>
                  <p>{formatDateTime(chamado.created_at)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-muted-foreground">Atualizado em</p>
                  <p>{formatDateTime(chamado.updated_at)}</p>
                </div>
              </div>
              {chamado.status_kanban !== "concluido" && (
                <div className="flex items-center gap-3 text-sm text-orange-600 dark:text-orange-400">
                  <Clock className="h-4 w-4" />
                  <div>
                    <p>Tempo aberto</p>
                    <p className="font-medium">{formatTempoAberto(chamado.created_at)}</p>
                  </div>
                </div>
              )}
              {chamado.resolved_at && (
                <div className="flex items-center gap-3 text-sm text-green-600">
                  <Clock className="h-4 w-4" />
                  <div>
                    <p>Resolvido em</p>
                    <p>{formatDateTime(chamado.resolved_at)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}
