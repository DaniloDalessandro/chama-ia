"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { toast } from "@/components/ui/sonner"
import {
  Brain,
  AlertTriangle,
  RefreshCw,
  Check,
  Loader2,
  Tag,
  TrendingUp,
  FileText,
  Link2,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"
import {
  chamadoAdminService,
  type ChamadoDetail,
} from "@/services/chamado-admin.service"

interface IAClassificationCardProps {
  chamado: ChamadoDetail
  onUpdate: () => void
}

const categoriaLabels: Record<string, string> = {
  financeiro: "Financeiro / Pagamento",
  nota_fiscal: "Nota Fiscal / Boletos",
  problema_tecnico: "Problema Tecnico",
  login_acesso: "Login / Acesso",
  cadastro_dados: "Cadastro / Dados",
  atendimento: "Atendimento / Suporte",
  solicitacao_servico: "Solicitacao de Servico",
  reclamacao: "Reclamacao Geral",
  outros: "Outros",
}

const prioridadeColors: Record<string, string> = {
  baixa: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  media: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  alta: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
  urgente: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
}

const prioridadeLabels: Record<string, string> = {
  baixa: "Baixa",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
}

function formatDate(dateString: string | null) {
  if (!dateString) return null
  return new Date(dateString).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function IAClassificationCard({ chamado, onUpdate }: IAClassificationCardProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [isApplying, setIsApplying] = useState(false)

  const handleProcessarIA = async () => {
    setIsProcessing(true)
    try {
      const response = await chamadoAdminService.processarIA(chamado.id) as any
      if (response.success) {
        if (response.prioridade_auto_aplicada) {
          toast.success("IA processou e aplicou prioridade URGENTE automaticamente!", {
            description: "Chamado detectado como financeiro",
            duration: 5000,
          })
        } else {
          toast.success(response.message || "Processamento IA concluido!")
        }
        onUpdate()
      } else {
        toast.error(response.message || "Erro ao processar com IA")
      }
    } catch (err) {
      toast.error("Erro ao processar com IA")
    } finally {
      setIsProcessing(false)
    }
  }

  const handleAplicarClassificacao = async () => {
    setIsApplying(true)
    try {
      const response = await chamadoAdminService.aplicarClassificacaoIA(chamado.id)
      if (response.success) {
        toast.success("Prioridade sugerida aplicada!")
        onUpdate()
      } else {
        toast.error(response.message || "Erro ao aplicar classificacao")
      }
    } catch (err) {
      toast.error("Erro ao aplicar classificacao")
    } finally {
      setIsApplying(false)
    }
  }

  const prioridadesDiferentes = chamado.prioridade !== chamado.ia_prioridade_sugerida
  const jaEhUrgente = chamado.prioridade === "urgente"

  return (
    <Card className="border-purple-200 dark:border-purple-900">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Brain className="h-5 w-5 text-purple-500" />
          Classificacao IA
          {chamado.ia_processed && (
            <Badge variant="secondary" className="ml-auto text-xs bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
              <Sparkles className="h-3 w-3 mr-1" />
              Processado
            </Badge>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {!chamado.ia_processed ? (
          // Ainda nao processado
          <div className="text-center py-4 space-y-3">
            <p className="text-sm text-muted-foreground">
              Este chamado ainda nao foi processado pela IA.
            </p>
            <Button
              onClick={handleProcessarIA}
              disabled={isProcessing}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4 mr-2" />
                  Processar com IA
                </>
              )}
            </Button>
          </div>
        ) : (
          // Ja processado - mostrar resultados
          <>
            {/* Categoria e Prioridade Sugerida */}
            <div className="flex flex-wrap gap-2">
              {chamado.ia_categoria && (
                <Badge variant="outline" className="flex items-center gap-1">
                  <Tag className="h-3 w-3" />
                  {categoriaLabels[chamado.ia_categoria] || chamado.ia_categoria}
                </Badge>
              )}
              {chamado.ia_prioridade_sugerida && (
                <Badge
                  variant="secondary"
                  className={cn(
                    "flex items-center gap-1",
                    prioridadeColors[chamado.ia_prioridade_sugerida]
                  )}
                >
                  <TrendingUp className="h-3 w-3" />
                  Sugerida: {prioridadeLabels[chamado.ia_prioridade_sugerida] || chamado.ia_prioridade_sugerida}
                </Badge>
              )}
            </div>

            {/* Resumo IA */}
            {chamado.ia_resumo && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
                  <FileText className="h-3 w-3" />
                  Resumo IA
                </div>
                <p className="text-sm bg-muted/50 rounded-md p-2">
                  {chamado.ia_resumo}
                </p>
              </div>
            )}

            {/* Palavras-chave */}
            {chamado.ia_palavras_chave && chamado.ia_palavras_chave.length > 0 && (
              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">
                  Palavras-chave
                </div>
                <div className="flex flex-wrap gap-1">
                  {chamado.ia_palavras_chave.map((keyword, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {keyword}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Alerta de Chamado Recorrente */}
            {chamado.is_recorrente && chamado.chamado_similar && (
              <>
                <Separator />
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-3 space-y-2">
                  <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span className="font-medium text-sm">Chamado Recorrente Detectado</span>
                  </div>
                  <p className="text-xs text-yellow-600 dark:text-yellow-500">
                    Similaridade: {Math.round((chamado.similaridade_score || 0) * 100)}%
                  </p>
                  <div className="flex items-center gap-2 text-sm">
                    <Link2 className="h-3 w-3" />
                    <span className="font-medium">#{chamado.chamado_similar.protocolo}</span>
                    <span className="text-muted-foreground truncate">
                      {chamado.chamado_similar.assunto}
                    </span>
                  </div>
                  {chamado.chamado_similar.resolved_at && (
                    <p className="text-xs text-muted-foreground">
                      Resolvido em: {formatDate(chamado.chamado_similar.resolved_at)}
                    </p>
                  )}
                </div>
              </>
            )}

            <Separator />

            {/* Acoes */}
            <div className="flex flex-wrap gap-2">
              {/* Botao Aplicar Prioridade - so mostra se diferente */}
              {prioridadesDiferentes && chamado.ia_prioridade_sugerida && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleAplicarClassificacao}
                  disabled={isApplying}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isApplying ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4 mr-1" />
                  )}
                  Aplicar Prioridade
                </Button>
              )}

              {/* Botao Reprocessar */}
              <Button
                size="sm"
                variant="outline"
                onClick={handleProcessarIA}
                disabled={isProcessing}
              >
                {isProcessing ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-1" />
                )}
                Reprocessar
              </Button>
            </div>

            {/* Data do processamento */}
            {chamado.ia_processed_at && (
              <p className="text-xs text-muted-foreground text-right">
                Processado em: {formatDate(chamado.ia_processed_at)}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
