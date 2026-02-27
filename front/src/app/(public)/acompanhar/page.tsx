"use client"

import { useState } from "react"
import Link from "next/link"
import { Navbar, Footer } from "@/components/landing"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Search,
  Mail,
  FileText,
  Clock,
  ArrowLeft,
  Paperclip,
  MessageSquare,
  History,
  Loader2,
  AlertCircle,
  ChevronRight,
} from "lucide-react"
import {
  chamadoService,
  type ChamadoConsultaProtocoloResponse,
  type ChamadoResumoEmail,
} from "@/services/ticket.service"

type TabType = "protocolo" | "email"

const STATUS_COLORS: Record<string, string> = {
  aberto: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  em_analise: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  em_atendimento: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  aguardando_cliente: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  resolvido: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  fechado: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
  cancelado: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
}

const PRIORIDADE_COLORS: Record<string, string> = {
  baixa: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  media: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  alta: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400",
  urgente: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatDateShort(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
}

export default function AcompanharPage() {
  const [activeTab, setActiveTab] = useState<TabType>("protocolo")
  const [protocolo, setProtocolo] = useState("")
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  // Resultados
  const [chamadoDetail, setChamadoDetail] = useState<ChamadoConsultaProtocoloResponse | null>(null)
  const [chamadosList, setChamadosList] = useState<ChamadoResumoEmail[]>([])
  const [totalChamados, setTotalChamados] = useState(0)
  const [showDetail, setShowDetail] = useState(false)

  const handleBuscarProtocolo = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!protocolo.trim()) return

    setLoading(true)
    setError("")
    setChamadoDetail(null)

    try {
      const response = await chamadoService.consultarPorProtocolo(protocolo.trim())
      if (response.success && response.data) {
        setChamadoDetail(response.data)
        setShowDetail(true)
      } else {
        setError(response.message || "Chamado nao encontrado.")
      }
    } catch {
      setError("Erro ao buscar chamado. Tente novamente.")
    } finally {
      setLoading(false)
    }
  }

  const handleBuscarEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setLoading(true)
    setError("")
    setChamadosList([])
    setShowDetail(false)
    setChamadoDetail(null)

    try {
      const response = await chamadoService.listarPorEmail(email.trim())
      if (response.success && response.data) {
        setChamadosList(response.data)
        setTotalChamados(response.total || response.data.length)
      } else {
        setError(response.message || "Nenhum chamado encontrado.")
      }
    } catch {
      setError("Erro ao buscar chamados. Tente novamente.")
    } finally {
      setLoading(false)
    }
  }

  const handleVerDetalhes = async (protocoloItem: string) => {
    setLoading(true)
    setError("")

    try {
      const response = await chamadoService.consultarPorProtocolo(protocoloItem)
      if (response.success && response.data) {
        setChamadoDetail(response.data)
        setShowDetail(true)
      } else {
        setError(response.message || "Erro ao carregar detalhes.")
      }
    } catch {
      setError("Erro ao carregar detalhes. Tente novamente.")
    } finally {
      setLoading(false)
    }
  }

  const handleVoltar = () => {
    setShowDetail(false)
    setChamadoDetail(null)
    setError("")
  }

  const resetAll = () => {
    setChamadoDetail(null)
    setChamadosList([])
    setShowDetail(false)
    setError("")
    setProtocolo("")
    setEmail("")
  }

  return (
    <>
      <Navbar />

      <main className="min-h-screen bg-gradient-to-b from-background to-muted/30 pt-24 pb-16">
        <div className="container mx-auto max-w-4xl px-4">
          {/* Header */}
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Search className="h-8 w-8 text-primary" />
            </div>
            <h1 className="mb-3 text-3xl font-bold tracking-tight md:text-4xl">
              Acompanhar Chamados
            </h1>
            <p className="mx-auto max-w-xl text-muted-foreground">
              Digite o numero do protocolo para acompanhar o andamento do chamado.
              Ou, se preferir, informe seu e-mail para visualizar todos os protocolos
              ja abertos e acessar o historico completo.
            </p>
          </div>

          {/* Search Card */}
          {!showDetail && (
            <Card className="mb-8 shadow-lg">
              <CardContent className="p-6">
                {/* Tabs */}
                <div className="mb-6 flex gap-2 rounded-lg bg-muted p-1">
                  <button
                    onClick={() => { setActiveTab("protocolo"); setError(""); setChamadosList([]); }}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-all ${
                      activeTab === "protocolo"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <FileText className="h-4 w-4" />
                    Por Protocolo
                  </button>
                  <button
                    onClick={() => { setActiveTab("email"); setError(""); setChamadoDetail(null); }}
                    className={`flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-all ${
                      activeTab === "email"
                        ? "bg-background text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Mail className="h-4 w-4" />
                    Por E-mail
                  </button>
                </div>

                {/* Search Forms */}
                {activeTab === "protocolo" ? (
                  <form onSubmit={handleBuscarProtocolo} className="flex gap-3">
                    <Input
                      placeholder="Digite o numero do protocolo (ex: 0001/2026)"
                      value={protocolo}
                      onChange={(e) => setProtocolo(e.target.value)}
                      className="flex-1"
                    />
                    <Button type="submit" disabled={loading || !protocolo.trim()}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buscar"}
                    </Button>
                  </form>
                ) : (
                  <form onSubmit={handleBuscarEmail} className="flex gap-3">
                    <Input
                      type="email"
                      placeholder="Digite seu e-mail"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="flex-1"
                    />
                    <Button type="submit" disabled={loading || !email.trim()}>
                      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Consultar"}
                    </Button>
                  </form>
                )}

                {/* Error */}
                {error && (
                  <div className="mt-4 flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    {error}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Email List Results */}
          {activeTab === "email" && chamadosList.length > 0 && !showDetail && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">
                  {totalChamados} chamado{totalChamados !== 1 ? "s" : ""} encontrado{totalChamados !== 1 ? "s" : ""}
                </h2>
                <Button variant="ghost" size="sm" onClick={resetAll}>
                  Nova consulta
                </Button>
              </div>

              {chamadosList.map((item) => (
                <Card key={item.protocolo} className="transition-shadow hover:shadow-md">
                  <CardContent className="flex items-center justify-between p-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-bold text-primary">
                          #{item.protocolo}
                        </span>
                        <Badge className={STATUS_COLORS[item.status] || "bg-gray-100 text-gray-800"}>
                          {item.status_display}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium">{item.assunto}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Aberto em {formatDateShort(item.created_at)}
                        </span>
                        <span>Atualizado em {formatDateShort(item.updated_at)}</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleVerDetalhes(item.protocolo)}
                      disabled={loading}
                    >
                      Ver detalhes
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Detail View */}
          {showDetail && chamadoDetail && (
            <div className="space-y-6">
              {/* Back Button */}
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={handleVoltar}>
                  <ArrowLeft className="mr-1 h-4 w-4" />
                  Voltar
                </Button>
                <Button variant="ghost" size="sm" onClick={resetAll}>
                  Nova consulta
                </Button>
              </div>

              {/* Main Info Card */}
              <Card className="shadow-lg">
                <CardHeader className="pb-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Protocolo</p>
                      <CardTitle className="font-mono text-2xl text-primary">
                        #{chamadoDetail.protocolo}
                      </CardTitle>
                    </div>
                    <div className="flex gap-2">
                      <Badge className={`text-sm ${STATUS_COLORS[chamadoDetail.status] || ""}`}>
                        {chamadoDetail.status_display}
                      </Badge>
                      <Badge className={`text-sm ${PRIORIDADE_COLORS[chamadoDetail.prioridade] || ""}`}>
                        {chamadoDetail.prioridade_display}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <p className="text-xs font-medium uppercase text-muted-foreground">Assunto</p>
                      <p className="text-sm font-medium">{chamadoDetail.assunto}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-muted-foreground">Categoria</p>
                      <p className="text-sm font-medium">{chamadoDetail.tipo_display}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-muted-foreground">Data de Abertura</p>
                      <p className="text-sm">{formatDate(chamadoDetail.created_at)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium uppercase text-muted-foreground">Ultima Atualizacao</p>
                      <p className="text-sm">{formatDate(chamadoDetail.updated_at)}</p>
                    </div>
                    {chamadoDetail.resolved_at && (
                      <div>
                        <p className="text-xs font-medium uppercase text-muted-foreground">Resolvido em</p>
                        <p className="text-sm">{formatDate(chamadoDetail.resolved_at)}</p>
                      </div>
                    )}
                  </div>

                  <div>
                    <p className="mb-1 text-xs font-medium uppercase text-muted-foreground">Descricao</p>
                    <div className="rounded-lg bg-muted/50 p-4 text-sm leading-relaxed">
                      {chamadoDetail.descricao}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Timeline / History */}
              {chamadoDetail.historico_publico && chamadoDetail.historico_publico.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <History className="h-4 w-4" />
                      Historico
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {chamadoDetail.historico_publico.map((item, index) => (
                        <div key={item.id} className="flex gap-3">
                          <div className="relative flex flex-col items-center">
                            <div className="h-2.5 w-2.5 rounded-full bg-primary" />
                            {index < chamadoDetail.historico_publico.length - 1 && (
                              <div className="mt-1 w-px flex-1 bg-border" />
                            )}
                          </div>
                          <div className="flex-1 pb-4">
                            <p className="text-sm font-medium">{item.descricao}</p>
                            <p className="text-xs text-muted-foreground">
                              {formatDate(item.created_at)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Comments */}
              {chamadoDetail.comentarios_publicos && chamadoDetail.comentarios_publicos.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <MessageSquare className="h-4 w-4" />
                      Mensagens ({chamadoDetail.comentarios_publicos.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {chamadoDetail.comentarios_publicos.map((comment) => (
                        <div
                          key={comment.id}
                          className="rounded-lg border bg-muted/30 p-4"
                        >
                          <div className="mb-2 flex items-center justify-between">
                            <span className="text-sm font-medium">
                              {comment.autor_nome || "Suporte"}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(comment.created_at)}
                            </span>
                          </div>
                          <p className="text-sm leading-relaxed">{comment.conteudo}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Attachments */}
              {chamadoDetail.anexos && chamadoDetail.anexos.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Paperclip className="h-4 w-4" />
                      Anexos ({chamadoDetail.anexos.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {chamadoDetail.anexos.map((anexo) => (
                        <div
                          key={anexo.id}
                          className="flex items-center justify-between rounded-lg border p-3"
                        >
                          <div className="flex items-center gap-3">
                            <Paperclip className="h-4 w-4 text-muted-foreground" />
                            <div>
                              <p className="text-sm font-medium">{anexo.nome_original}</p>
                              <p className="text-xs text-muted-foreground">
                                {(anexo.tamanho / 1024).toFixed(1)} KB
                              </p>
                            </div>
                          </div>
                          {anexo.url && (
                            <Button variant="ghost" size="sm" asChild>
                              <a href={anexo.url} target="_blank" rel="noopener noreferrer">
                                Baixar
                              </a>
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* No results state (initial) */}
          {!showDetail && chamadosList.length === 0 && !chamadoDetail && !error && !loading && (
            <div className="mt-4 text-center text-sm text-muted-foreground">
              <Link href="/atendimento" className="text-primary hover:underline">
                Precisa abrir um novo chamado? Clique aqui
              </Link>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </>
  )
}
