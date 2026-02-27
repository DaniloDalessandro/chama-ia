"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import {
  Send,
  CheckCircle,
  FileText,
  AlertCircle,
  DollarSign,
  HelpCircle,
  Loader2,
  Upload,
  X,
  File,
  Tag,
  ArrowUpCircle,
  Brain,
  Lightbulb,
  Copy,
} from "lucide-react"
import {
  chamadoService,
  type ChamadoCreateResponse,
  type IAProcessamentoResponse,
} from "@/services/ticket.service"

const ticketTypes = [
  { value: "nota-fiscal", label: "Nota Fiscal", icon: FileText },
  { value: "erro-sistema", label: "Erro no Sistema", icon: AlertCircle },
  { value: "financeiro", label: "Financeiro", icon: DollarSign },
  { value: "outros", label: "Outros", icon: HelpCircle }
]

const ACCEPTED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"]
}

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_FILES = 5

type ModalPhase = "created" | "processing" | "solution_found" | "no_solution" | "error"

interface TicketFormData {
  name: string
  email: string
  cliente: string
  type: string
  subject: string
  description: string
}

interface Cliente {
  id: number
  nome: string
  nome_fantasia: string
  cnpj: string
}

interface FileWithPreview extends File {
  preview?: string
}

export function TicketForm() {
  const [formData, setFormData] = useState<TicketFormData>({
    name: "",
    email: "",
    cliente: "",
    type: "",
    subject: "",
    description: ""
  })
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loadingClientes, setLoadingClientes] = useState(true)
  const [files, setFiles] = useState<FileWithPreview[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [errors, setErrors] = useState<Partial<TicketFormData>>({})

  // Modal states
  const [modalOpen, setModalOpen] = useState(false)
  const [modalPhase, setModalPhase] = useState<ModalPhase>("created")
  const [createResponse, setCreateResponse] = useState<ChamadoCreateResponse | null>(null)
  const [iaResponse, setIaResponse] = useState<IAProcessamentoResponse | null>(null)
  const [progressValue, setProgressValue] = useState(0)
  const [copied, setCopied] = useState(false)

  // Carregar lista de clientes
  useEffect(() => {
    const fetchClientes = async () => {
      try {
        const response = await fetch('/api/v1/clientes/publico/')
        if (response.ok) {
          const data = await response.json()
          setClientes(data)
        }
      } catch (error) {
        console.error('Erro ao carregar clientes:', error)
      } finally {
        setLoadingClientes(false)
      }
    }

    fetchClientes()
  }, [])

  // Progress bar animation during processing
  useEffect(() => {
    if (modalPhase !== "processing") return

    setProgressValue(0)
    const interval = setInterval(() => {
      setProgressValue((prev) => {
        if (prev >= 90) {
          clearInterval(interval)
          return 90
        }
        return prev + Math.random() * 8 + 2
      })
    }, 400)

    return () => clearInterval(interval)
  }, [modalPhase])

  const processIA = useCallback(async (chamadoId: number) => {
    setModalPhase("processing")

    try {
      const iaResult = await chamadoService.processarIA(chamadoId)

      setProgressValue(100)

      // Small delay so the user sees 100%
      await new Promise((r) => setTimeout(r, 500))

      if (iaResult.success && iaResult.data) {
        setIaResponse(iaResult.data)
        if (iaResult.data.is_recorrente && iaResult.data.solucao_similar) {
          setModalPhase("solution_found")
        } else {
          setModalPhase("no_solution")
        }
      } else {
        setModalPhase("error")
      }
    } catch {
      setModalPhase("error")
    }
  }, [])

  const resetForm = useCallback(() => {
    setFormData({ name: "", email: "", cliente: "", type: "", subject: "", description: "" })
    files.forEach((file) => {
      if (file.preview) URL.revokeObjectURL(file.preview)
    })
    setFiles([])
    setFileError(null)
    setSubmitError(null)
    setErrors({})
    setCreateResponse(null)
    setIaResponse(null)
    setProgressValue(0)
    setCopied(false)
  }, [files])

  const handleModalClose = (open: boolean) => {
    // Block closing during processing
    if (!open && modalPhase === "processing") return
    if (!open) {
      setModalOpen(false)
      resetForm()
    }
  }

  const copyProtocolo = () => {
    if (!createResponse) return
    navigator.clipboard.writeText(createResponse.protocolo)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return
    setFileError(null)

    const newFiles: FileWithPreview[] = []

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i]

      if (files.length + newFiles.length >= MAX_FILES) {
        setFileError(`Maximo de ${MAX_FILES} arquivos permitidos`)
        break
      }

      const isValidType = Object.keys(ACCEPTED_FILE_TYPES).includes(file.type)
      if (!isValidType) {
        setFileError("Tipo de arquivo nao permitido. Use PDF, JPG, PNG ou WebP")
        continue
      }

      if (file.size > MAX_FILE_SIZE) {
        setFileError("Arquivo muito grande. Maximo 5MB por arquivo")
        continue
      }

      const fileWithPreview = file as FileWithPreview
      if (file.type.startsWith("image/")) {
        fileWithPreview.preview = URL.createObjectURL(file)
      }

      newFiles.push(fileWithPreview)
    }

    setFiles(prev => [...prev, ...newFiles])
  }

  const removeFile = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev]
      const removed = newFiles.splice(index, 1)[0]
      if (removed.preview) {
        URL.revokeObjectURL(removed.preview)
      }
      return newFiles
    })
    setFileError(null)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files)
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B"
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
    return (bytes / (1024 * 1024)).toFixed(1) + " MB"
  }

  const validateForm = () => {
    const newErrors: Partial<TicketFormData> = {}

    if (!formData.name.trim()) {
      newErrors.name = "Nome e obrigatorio"
    }
    if (!formData.email.trim()) {
      newErrors.email = "E-mail e obrigatorio"
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "E-mail invalido"
    }
    if (!formData.type) {
      newErrors.type = "Selecione o tipo de solicitacao"
    }
    if (!formData.subject.trim()) {
      newErrors.subject = "Assunto e obrigatorio"
    }
    if (!formData.description.trim()) {
      newErrors.description = "Descricao e obrigatoria"
    } else if (formData.description.length < 20) {
      newErrors.description = "Descreva com mais detalhes (minimo 20 caracteres)"
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      // Phase 1: Create chamado (fast)
      const response = await chamadoService.create({
        nome: formData.name,
        email: formData.email,
        cliente: formData.cliente ? parseInt(formData.cliente) : undefined,
        tipo: formData.type,
        assunto: formData.subject,
        descricao: formData.description,
        anexos: files.length > 0 ? files : undefined,
      })

      if (response.success && response.data) {
        setCreateResponse(response.data)
        setModalPhase("created")
        setModalOpen(true)

        // Phase 2: Process IA (async in modal)
        processIA(response.data.id)
      } else {
        setSubmitError(response.message || "Erro ao enviar chamado. Tente novamente.")
      }
    } catch (error) {
      console.error("Erro ao enviar chamado:", error)
      setSubmitError("Erro de conexao. Verifique sua internet e tente novamente.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleChange = (field: keyof TicketFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }))
    }
  }

  // =============================================
  // Modal content per phase
  // =============================================

  const renderModalContent = () => {
    if (!createResponse) return null

    const protocoloBlock = (
      <div className="flex items-center justify-center gap-2">
        <p className="text-lg font-bold text-foreground">
          Protocolo: {createResponse.protocolo}
        </p>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={copyProtocolo}
          title="Copiar protocolo"
        >
          {copied ? (
            <CheckCircle className="h-4 w-4 text-green-500" />
          ) : (
            <Copy className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </div>
    )

    switch (modalPhase) {
      case "created":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                Chamado registrado!
              </DialogTitle>
              <DialogDescription className="text-center">
                Seu chamado foi salvo com sucesso. Iniciando analise...
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col items-center gap-4 py-4">
              {protocoloBlock}
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Iniciando analise inteligente...
              </div>
            </div>
          </>
        )

      case "processing":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <Brain className="h-5 w-5 text-primary animate-pulse" />
                Analisando seu chamado...
              </DialogTitle>
              <DialogDescription className="text-center">
                Nossa IA esta analisando seu chamado para oferecer a melhor solucao.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col items-center gap-4 py-4">
              {protocoloBlock}
              <div className="w-full space-y-2">
                <Progress value={progressValue} className="h-2" />
                <p className="text-center text-sm text-muted-foreground">
                  {progressValue < 30
                    ? "Classificando chamado..."
                    : progressValue < 60
                      ? "Buscando solucoes similares..."
                      : "Finalizando analise..."}
                </p>
              </div>
            </div>
          </>
        )

      case "solution_found":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <Lightbulb className="h-5 w-5 text-yellow-500" />
                Solucao encontrada!
              </DialogTitle>
              <DialogDescription className="text-center">
                Encontramos um chamado similar que ja foi resolvido.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-4">
              {protocoloBlock}

              {/* Card da solucao similar */}
              {iaResponse?.solucao_similar && (
                <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
                  <div className="flex items-start gap-2">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <div>
                      <span className="font-medium text-foreground">Chamado similar: </span>
                      <span className="text-muted-foreground">{iaResponse.solucao_similar.assunto}</span>
                    </div>
                  </div>
                  {iaResponse.solucao_similar.ia_resumo && (
                    <div className="flex items-start gap-2">
                      <Brain className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      <div>
                        <span className="font-medium text-foreground">Resumo: </span>
                        <span className="text-muted-foreground">{iaResponse.solucao_similar.ia_resumo}</span>
                      </div>
                    </div>
                  )}
                  {iaResponse.solucao_similar.comentarios_publicos.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-foreground">Solucao aplicada:</p>
                      {iaResponse.solucao_similar.comentarios_publicos.map((c) => (
                        <div key={c.id} className="rounded border bg-background p-3 text-sm">
                          <p className="text-muted-foreground">{c.conteudo}</p>
                          <p className="mt-1 text-xs text-muted-foreground/70">
                            {c.autor_nome} - {new Date(c.created_at).toLocaleDateString("pt-BR")}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Classificacao IA */}
              {iaResponse && (
                <div className="rounded-lg border bg-primary/5 p-4 space-y-2">
                  <p className="text-sm font-medium text-foreground flex items-center gap-1.5">
                    <Brain className="h-4 w-4 text-primary" />
                    Classificacao IA
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {iaResponse.ia_categoria && (
                      <div className="flex items-center gap-1.5">
                        <Tag className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-muted-foreground">{iaResponse.ia_categoria}</span>
                      </div>
                    )}
                    {iaResponse.ia_prioridade_sugerida && (
                      <div className="flex items-center gap-1.5">
                        <ArrowUpCircle className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-muted-foreground">{iaResponse.ia_prioridade_sugerida}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button onClick={() => handleModalClose(false)} className="w-full">
                Entendi, obrigado!
              </Button>
            </DialogFooter>
          </>
        )

      case "no_solution":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <CheckCircle className="h-5 w-5 text-blue-500" />
                Chamado encaminhado para analise
              </DialogTitle>
              <DialogDescription className="text-center">
                Seu chamado foi classificado e encaminhado para nossa equipe.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-4">
              {protocoloBlock}

              {/* Classificacao IA */}
              {iaResponse && (
                <div className="rounded-lg border bg-primary/5 p-4 space-y-3">
                  <p className="text-sm font-medium text-foreground flex items-center gap-1.5">
                    <Brain className="h-4 w-4 text-primary" />
                    Classificacao automatica
                  </p>
                  <div className="space-y-2 text-sm">
                    {iaResponse.ia_categoria && (
                      <div className="flex items-center gap-2">
                        <Tag className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="font-medium text-foreground">Categoria: </span>
                        <span className="text-muted-foreground">{iaResponse.ia_categoria}</span>
                      </div>
                    )}
                    {iaResponse.ia_prioridade_sugerida && (
                      <div className="flex items-center gap-2">
                        <ArrowUpCircle className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="font-medium text-foreground">Prioridade: </span>
                        <span className="text-muted-foreground">{iaResponse.ia_prioridade_sugerida}</span>
                      </div>
                    )}
                    {iaResponse.ia_resumo && (
                      <div className="flex items-start gap-2">
                        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                        <div>
                          <span className="font-medium text-foreground">Resumo: </span>
                          <span className="text-muted-foreground">{iaResponse.ia_resumo}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <p className="text-center text-sm text-muted-foreground">
                Nossa equipe ira analisar sua solicitacao e entrar em contato em breve.
              </p>
            </div>
            <DialogFooter>
              <Button onClick={() => handleModalClose(false)} className="w-full">
                Fechar
              </Button>
            </DialogFooter>
          </>
        )

      case "error":
        return (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center justify-center gap-2">
                <AlertCircle className="h-5 w-5 text-yellow-500" />
                Chamado registrado
              </DialogTitle>
              <DialogDescription className="text-center">
                Seu chamado foi salvo, mas a analise automatica esta temporariamente indisponivel.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col items-center gap-4 py-4">
              {protocoloBlock}
              <p className="text-center text-sm text-muted-foreground">
                Nao se preocupe! Sua solicitacao foi registrada e nossa equipe ira analisar manualmente.
                Guarde o numero de protocolo para acompanhamento.
              </p>
            </div>
            <DialogFooter>
              <Button onClick={() => handleModalClose(false)} className="w-full">
                Fechar
              </Button>
            </DialogFooter>
          </>
        )
    }
  }

  return (
    <section id="chamados" className="py-24 bg-background">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="mx-auto max-w-3xl text-center mb-12">
          <span className="mb-4 inline-block rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
            Suporte
          </span>
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Abertura de <span className="text-primary">Chamados</span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Precisa de ajuda? Abra um chamado e nossa equipe entrara em contato o mais rapido possivel.
          </p>
        </div>

        <div className="mx-auto max-w-2xl">
          <Card className="shadow-lg">
            <CardHeader>
              <CardTitle>Novo Chamado</CardTitle>
              <CardDescription>
                Preencha os campos abaixo com o maximo de detalhes para agilizar o atendimento.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Nome */}
                  <div className="space-y-2">
                    <Label htmlFor="name">Nome completo *</Label>
                    <Input
                      id="name"
                      placeholder="Seu nome"
                      value={formData.name}
                      onChange={(e) => handleChange("name", e.target.value)}
                      className={errors.name ? "border-destructive" : ""}
                    />
                    {errors.name && (
                      <p className="text-sm text-destructive">{errors.name}</p>
                    )}
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <Label htmlFor="email">E-mail *</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="seu@email.com"
                      value={formData.email}
                      onChange={(e) => handleChange("email", e.target.value)}
                      className={errors.email ? "border-destructive" : ""}
                    />
                    {errors.email && (
                      <p className="text-sm text-destructive">{errors.email}</p>
                    )}
                  </div>
                </div>

                {/* Empresa/Cliente */}
                <div className="space-y-2">
                  <Label>Empresa (opcional)</Label>
                  <Select
                    value={formData.cliente}
                    onValueChange={(value) => handleChange("cliente", value)}
                    disabled={loadingClientes}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={loadingClientes ? "Carregando empresas..." : "Selecione sua empresa"} />
                    </SelectTrigger>
                    <SelectContent>
                      {clientes.map((cliente) => (
                        <SelectItem key={cliente.id} value={cliente.id.toString()}>
                          {cliente.nome_fantasia || cliente.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Tipo de solicitacao */}
                <div className="space-y-2">
                  <Label>Tipo de solicitacao *</Label>
                  <Select
                    value={formData.type}
                    onValueChange={(value) => handleChange("type", value)}
                  >
                    <SelectTrigger className={errors.type ? "border-destructive" : ""}>
                      <SelectValue placeholder="Selecione o tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      {ticketTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          <div className="flex items-center gap-2">
                            <type.icon className="h-4 w-4" />
                            {type.label}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.type && (
                    <p className="text-sm text-destructive">{errors.type}</p>
                  )}
                </div>

                {/* Assunto */}
                <div className="space-y-2">
                  <Label htmlFor="subject">Assunto *</Label>
                  <Input
                    id="subject"
                    placeholder="Resumo do problema ou solicitacao"
                    value={formData.subject}
                    onChange={(e) => handleChange("subject", e.target.value)}
                    className={errors.subject ? "border-destructive" : ""}
                  />
                  {errors.subject && (
                    <p className="text-sm text-destructive">{errors.subject}</p>
                  )}
                </div>

                {/* Descricao */}
                <div className="space-y-2">
                  <Label htmlFor="description">Descricao detalhada *</Label>
                  <Textarea
                    id="description"
                    placeholder="Descreva o problema ou solicitacao com o maximo de detalhes possivel..."
                    rows={5}
                    value={formData.description}
                    onChange={(e) => handleChange("description", e.target.value)}
                    className={errors.description ? "border-destructive" : ""}
                  />
                  {errors.description && (
                    <p className="text-sm text-destructive">{errors.description}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {formData.description.length}/500 caracteres
                  </p>
                </div>

                {/* Anexos */}
                <div className="space-y-2">
                  <Label>Anexos (opcional)</Label>
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`
                      relative cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors
                      ${isDragging
                        ? "border-primary bg-primary/5"
                        : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50"
                      }
                      ${fileError ? "border-destructive" : ""}
                    `}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".pdf,.jpg,.jpeg,.png,.webp"
                      onChange={(e) => handleFileSelect(e.target.files)}
                      className="hidden"
                    />
                    <Upload className={`mx-auto h-10 w-10 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
                    <p className="mt-2 text-sm font-medium text-foreground">
                      Arraste arquivos aqui ou clique para selecionar
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      PDF, JPG, PNG ou WebP (max. 5MB cada, ate {MAX_FILES} arquivos)
                    </p>
                  </div>

                  {fileError && (
                    <p className="text-sm text-destructive">{fileError}</p>
                  )}

                  {/* Lista de arquivos */}
                  {files.length > 0 && (
                    <div className="mt-4 space-y-2">
                      {files.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center gap-3 rounded-lg border bg-muted/30 p-3"
                        >
                          {file.preview ? (
                            <img
                              src={file.preview}
                              alt={file.name}
                              className="h-12 w-12 rounded object-cover"
                            />
                          ) : (
                            <div className="flex h-12 w-12 items-center justify-center rounded bg-red-100 dark:bg-red-900/30">
                              <File className="h-6 w-6 text-red-600 dark:text-red-400" />
                            </div>
                          )}

                          <div className="flex-1 min-w-0">
                            <p className="truncate text-sm font-medium text-foreground">
                              {file.name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {formatFileSize(file.size)}
                            </p>
                          </div>

                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              removeFile(index)
                            }}
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Erro de envio */}
                {submitError && (
                  <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
                    <p className="text-sm text-destructive">{submitError}</p>
                  </div>
                )}

                {/* Submit Button */}
                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      <Send className="mr-2 h-5 w-5" />
                      Enviar Chamado
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modal multi-phase */}
      <Dialog open={modalOpen} onOpenChange={handleModalClose}>
        <DialogContent
          className="sm:max-w-2xl max-h-[85vh] overflow-y-auto"
          onInteractOutside={(e) => {
            if (modalPhase === "processing") e.preventDefault()
          }}
          onEscapeKeyDown={(e) => {
            if (modalPhase === "processing") e.preventDefault()
          }}
        >
          {renderModalContent()}
        </DialogContent>
      </Dialog>
    </section>
  )
}
