"use client"

import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useTheme } from "@/contexts/ThemeContext"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { toast } from "@/components/ui/sonner"
import { Moon, Sun, Monitor, Loader2, Mail, RefreshCw } from "lucide-react"
import { emailConfigService, type EmailConfig } from "@/services/emailConfigService"

export default function ConfiguracoesPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()
  const isAdmin = user?.role === "admin"

  const [emailConfig, setEmailConfig] = useState<EmailConfig | null>(null)
  const [isLoadingEmailConfig, setIsLoadingEmailConfig] = useState(true)
  const [isSavingEmailConfig, setIsSavingEmailConfig] = useState(false)
  const [isCheckingNow, setIsCheckingNow] = useState(false)

  const [emailForm, setEmailForm] = useState({
    email: "",
    password: "",
    imap_host: "imap.gmail.com",
    imap_port: 993,
    use_ssl: true,
    folder: "INBOX",
    is_active: true,
  })

  const loadEmailConfig = useCallback(async () => {
    setIsLoadingEmailConfig(true)
    try {
      const data = await emailConfigService.get()
      setEmailConfig(data)
      if (data.configured) {
        setEmailForm((prev) => ({
          ...prev,
          email: data.email || "",
          imap_host: data.imap_host || "imap.gmail.com",
          imap_port: data.imap_port ?? 993,
          use_ssl: data.use_ssl ?? true,
          folder: data.folder || "INBOX",
          is_active: data.is_active ?? true,
        }))
      }
    } catch (err) {
      console.error("Erro ao carregar configuracao de email:", err)
    } finally {
      setIsLoadingEmailConfig(false)
    }
  }, [])

  useEffect(() => {
    if (isAdmin) {
      loadEmailConfig()
    } else {
      setIsLoadingEmailConfig(false)
    }
  }, [isAdmin, loadEmailConfig])

  const handleSaveEmailConfig = async () => {
    setIsSavingEmailConfig(true)
    try {
      const payload = { ...emailForm }
      if (!payload.password) {
        delete (payload as Partial<typeof payload>).password
      }
      const data = await emailConfigService.save(payload)
      setEmailConfig(data)
      setEmailForm((prev) => ({ ...prev, password: "" }))
      toast.success("Email de chamados salvo com sucesso!")
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao salvar configuracao")
    } finally {
      setIsSavingEmailConfig(false)
    }
  }

  const handleCheckNow = async () => {
    setIsCheckingNow(true)
    try {
      const result = await emailConfigService.checkNow()
      if (result.erros > 0) {
        toast.error(result.erro_msg || "Erro ao verificar emails")
      } else {
        toast.success(`Verificado! ${result.processados} chamado(s) novo(s) criado(s).`)
      }
      loadEmailConfig()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erro ao verificar emails")
    } finally {
      setIsCheckingNow(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Configurações</h1>
        <p className="text-muted-foreground">
          Gerencie suas preferências e configurações da conta.
        </p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Perfil</CardTitle>
            <CardDescription>
              Atualize suas informações pessoais.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nome</Label>
              <Input id="name" defaultValue={user?.name || ""} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue={user?.email || ""} disabled />
              <p className="text-sm text-muted-foreground">
                O email não pode ser alterado.
              </p>
            </div>
            <Button>Salvar alterações</Button>
          </CardContent>
        </Card>

        {isAdmin && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="h-5 w-5" />
                Email para Chamados
              </CardTitle>
              <CardDescription>
                Cadastre a caixa de email (IMAP) que receberá as solicitações. Cada email novo
                vira automaticamente um chamado em &quot;Chamados Novos&quot;.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoadingEmailConfig ? (
                <div className="flex items-center justify-center py-6">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <>
                  <div className="grid gap-2">
                    <Label htmlFor="ingest-email">Email</Label>
                    <Input
                      id="ingest-email"
                      type="email"
                      placeholder="chamados@suaempresa.com"
                      value={emailForm.email}
                      onChange={(e) => setEmailForm((p) => ({ ...p, email: e.target.value }))}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="ingest-password">Senha de app</Label>
                    <Input
                      id="ingest-password"
                      type="password"
                      placeholder={emailConfig?.configured ? "•••••••• (deixe em branco para manter)" : "Senha de app do email"}
                      value={emailForm.password}
                      onChange={(e) => setEmailForm((p) => ({ ...p, password: e.target.value }))}
                    />
                    <p className="text-sm text-muted-foreground">
                      Para Gmail, use uma &quot;Senha de app&quot; (myaccount.google.com &gt; Segurança).
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label htmlFor="ingest-host">Servidor IMAP</Label>
                      <Input
                        id="ingest-host"
                        placeholder="imap.gmail.com"
                        value={emailForm.imap_host}
                        onChange={(e) => setEmailForm((p) => ({ ...p, imap_host: e.target.value }))}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="ingest-port">Porta</Label>
                      <Input
                        id="ingest-port"
                        type="number"
                        value={emailForm.imap_port}
                        onChange={(e) => setEmailForm((p) => ({ ...p, imap_port: Number(e.target.value) }))}
                      />
                    </div>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="ingest-folder">Pasta</Label>
                    <Input
                      id="ingest-folder"
                      placeholder="INBOX"
                      value={emailForm.folder}
                      onChange={(e) => setEmailForm((p) => ({ ...p, folder: e.target.value }))}
                    />
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Usar SSL</Label>
                    </div>
                    <Switch
                      checked={emailForm.use_ssl}
                      onCheckedChange={(checked) => setEmailForm((p) => ({ ...p, use_ssl: checked }))}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Verificação automática ativa</Label>
                      <p className="text-sm text-muted-foreground">
                        Busca novos emails a cada 5 minutos.
                      </p>
                    </div>
                    <Switch
                      checked={emailForm.is_active}
                      onCheckedChange={(checked) => setEmailForm((p) => ({ ...p, is_active: checked }))}
                    />
                  </div>

                  {emailConfig?.configured && (
                    <p className="text-sm text-muted-foreground">
                      {emailConfig.last_checked_at
                        ? `Última verificação: ${new Date(emailConfig.last_checked_at).toLocaleString("pt-BR")} — ${emailConfig.total_processed} chamado(s) criado(s) no total.`
                        : "Ainda não verificado."}
                      {emailConfig.last_error && (
                        <span className="block text-destructive">Erro: {emailConfig.last_error}</span>
                      )}
                    </p>
                  )}

                  <div className="flex gap-2">
                    <Button onClick={handleSaveEmailConfig} disabled={isSavingEmailConfig}>
                      {isSavingEmailConfig && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Salvar
                    </Button>
                    {emailConfig?.configured && (
                      <Button variant="outline" onClick={handleCheckNow} disabled={isCheckingNow}>
                        {isCheckingNow ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="mr-2 h-4 w-4" />
                        )}
                        Verificar agora
                      </Button>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Aparência</CardTitle>
            <CardDescription>
              Personalize a aparência da interface.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col gap-4">
              <Label>Tema</Label>
              <div className="flex gap-2">
                <Button
                  variant={theme === "light" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTheme("light")}
                >
                  <Sun className="mr-2 h-4 w-4" />
                  Claro
                </Button>
                <Button
                  variant={theme === "dark" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTheme("dark")}
                >
                  <Moon className="mr-2 h-4 w-4" />
                  Escuro
                </Button>
                <Button
                  variant={theme === "system" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTheme("system")}
                >
                  <Monitor className="mr-2 h-4 w-4" />
                  Sistema
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notificações</CardTitle>
            <CardDescription>
              Configure suas preferências de notificação.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Notificações por email</Label>
                <p className="text-sm text-muted-foreground">
                  Receber atualizações importantes por email.
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Notificações push</Label>
                <p className="text-sm text-muted-foreground">
                  Receber notificações no navegador.
                </p>
              </div>
              <Switch />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Resumo semanal</Label>
                <p className="text-sm text-muted-foreground">
                  Receber um resumo semanal das atividades.
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Segurança</CardTitle>
            <CardDescription>
              Gerencie a segurança da sua conta.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="current-password">Senha atual</Label>
              <Input id="current-password" type="password" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="new-password">Nova senha</Label>
              <Input id="new-password" type="password" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="confirm-password">Confirmar nova senha</Label>
              <Input id="confirm-password" type="password" />
            </div>
            <Button>Alterar senha</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
