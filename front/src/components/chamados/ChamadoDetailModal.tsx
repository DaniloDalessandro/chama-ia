"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  chamadoAdminService,
  type Chamado,
  type ChamadoDetail,
} from "@/services/chamado-admin.service"

interface ChamadoDetailModalProps {
  chamado: Chamado | null
  isOpen: boolean
  onClose: () => void
  onUpdate: () => void
}

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

export function ChamadoDetailModal({
  chamado,
  isOpen,
  onClose,
  onUpdate,
}: ChamadoDetailModalProps) {
  const [detail, setDetail] = useState<ChamadoDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [newComment, setNewComment] = useState("")
  const [isSendingComment, setIsSendingComment] = useState(false)
  const [selectedPrioridade, setSelectedPrioridade] = useState("")

  useEffect(() => {
    if (chamado && isOpen) {
      fetchDetail()
      setSelectedPrioridade(chamado.prioridade)
    }
  }, [chamado, isOpen])

  const fetchDetail = async () => {
    if (!chamado) return
    setIsLoading(true)
    try {
      const data = await chamadoAdminService.get(chamado.id)
      setDetail(data)
    } catch (err) {
      toast.error("Erro ao carregar detalhes do chamado")
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendComment = async () => {
    if (!detail || !newComment.trim()) return

    setIsSendingComment(true)
    try {
      const response = await chamadoAdminService.addComentario(
        detail.id,
        newComment,
        "publico"
      )
      if (response.success) {
        toast.success("Comentario adicionado!")
        setNewComment("")
        fetchDetail()
        onUpdate()
      } else {
        toast.error(response.message || "Erro ao adicionar comentario")
      }
    } catch (err) {
      toast.error("Erro ao adicionar comentario")
    } finally {
      setIsSendingComment(false)
    }
  }

  const handlePrioridadeChange = async (value: string) => {
    if (!detail) return

    setSelectedPrioridade(value)
    try {
      const response = await chamadoAdminService.updatePrioridade(detail.id, value)
      if (response.success) {
        toast.success("Prioridade atualizada!")
        fetchDetail()
        onUpdate()
      } else {
        toast.error(response.message || "Erro ao atualizar prioridade")
        setSelectedPrioridade(detail.prioridade)
      }
    } catch (err) {
      toast.error("Erro ao atualizar prioridade")
      setSelectedPrioridade(detail.prioridade)
    }
  }

  if (!chamado) return null

  const TipoIcon = tipoIcons[chamado.tipo] || HelpCircle

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div
              className={cn(
                "h-3 w-3 rounded-full",
                statusKanbanColors[chamado.status_kanban]
              )}
            />
            <span>#{chamado.protocolo}</span>
            <Badge variant="outline" className="ml-auto">
              {chamado.status_kanban_display}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : detail ? (
          <div className="space-y-6">
            {/* Info principal */}
            <div className="space-y-4">
              <h3 className="text-xl font-semibold">{detail.assunto}</h3>

              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="flex items-center gap-1">
                  <TipoIcon className="h-3 w-3" />
                  {detail.tipo_display}
                </Badge>
                <Badge
                  variant="secondary"
                  className={cn(prioridadeColors[detail.prioridade])}
                >
                  {detail.prioridade_display}
                </Badge>
                <Badge variant="outline">{detail.origem_display}</Badge>
              </div>
            </div>

            <Separator />

            {/* Grid de informacoes */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Solicitante */}
              <div className="space-y-3">
                <h4 className="font-medium text-sm text-muted-foreground">
                  Solicitante
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span>{detail.nome}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <a
                      href={`mailto:${detail.email}`}
                      className="text-primary hover:underline"
                    >
                      {detail.email}
                    </a>
                  </div>
                  {detail.telefone && (
                    <div className="flex items-center gap-2 text-sm">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span>{detail.telefone}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Datas e Auditoria */}
              <div className="space-y-3">
                <h4 className="font-medium text-sm text-muted-foreground">
                  Informacoes
                </h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span>Criado: {formatDateTime(detail.created_at)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span>Atualizado: {formatDateTime(detail.updated_at)}</span>
                  </div>
                  {detail.resolved_at && (
                    <div className="flex items-center gap-2 text-sm text-green-600">
                      <Clock className="h-4 w-4" />
                      <span>Resolvido: {formatDateTime(detail.resolved_at)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <Separator />

            {/* Descricao */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-muted-foreground">
                Descricao
              </h4>
              <div className="rounded-lg bg-muted p-4 text-sm whitespace-pre-wrap">
                {detail.descricao}
              </div>
            </div>

            {/* Anexos */}
            {detail.anexos && detail.anexos.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                    <Paperclip className="h-4 w-4" />
                    Anexos ({detail.anexos.length})
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {detail.anexos.map((anexo) => (
                      <a
                        key={anexo.id}
                        href={anexo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted transition-colors"
                      >
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="truncate max-w-[150px]">
                          {anexo.nome_original}
                        </span>
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </a>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Prioridade */}
            <Separator />
            <div className="flex items-center gap-4">
              <h4 className="font-medium text-sm text-muted-foreground">
                Alterar Prioridade:
              </h4>
              <Select value={selectedPrioridade} onValueChange={handlePrioridadeChange}>
                <SelectTrigger className="w-[150px]">
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

            {/* Comentarios */}
            <Separator />
            <div className="space-y-4">
              <h4 className="font-medium text-sm text-muted-foreground flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Comentarios ({detail.comentarios?.length || 0})
              </h4>

              {/* Lista de comentarios */}
              {detail.comentarios && detail.comentarios.length > 0 && (
                <div className="space-y-3 max-h-[200px] overflow-y-auto">
                  {detail.comentarios.map((comentario) => (
                    <div
                      key={comentario.id}
                      className={cn(
                        "rounded-lg p-3 text-sm",
                        comentario.is_from_client
                          ? "bg-blue-50 dark:bg-blue-950/50 ml-8"
                          : "bg-muted mr-8"
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium">{comentario.autor_nome}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(comentario.created_at)}
                        </span>
                      </div>
                      <p className="whitespace-pre-wrap">{comentario.conteudo}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Novo comentario */}
              <div className="flex gap-2">
                <Textarea
                  placeholder="Escreva um comentario..."
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  className="resize-none"
                  rows={2}
                />
                <Button
                  onClick={handleSendComment}
                  disabled={!newComment.trim() || isSendingComment}
                  size="icon"
                  className="shrink-0"
                >
                  {isSendingComment ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* Historico */}
            {detail.historico && detail.historico.length > 0 && (
              <>
                <Separator />
                <details className="group">
                  <summary className="cursor-pointer font-medium text-sm text-muted-foreground hover:text-foreground transition-colors">
                    Historico de alteracoes ({detail.historico.length})
                  </summary>
                  <div className="mt-3 space-y-2 max-h-[200px] overflow-y-auto">
                    {detail.historico.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-start gap-3 text-sm border-l-2 border-muted pl-3 py-1"
                      >
                        <div className="flex-1">
                          <p>{item.descricao}</p>
                          <p className="text-xs text-muted-foreground">
                            {item.usuario_nome || "Sistema"} -{" "}
                            {formatDateTime(item.created_at)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
