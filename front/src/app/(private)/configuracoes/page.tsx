"use client"

import { useAuth } from "@/hooks/useAuth"
import { useTheme } from "@/context/ThemeContext"
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
import { Moon, Sun, Monitor } from "lucide-react"

export default function ConfiguracoesPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()

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
