"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuth } from "@/hooks/useAuth"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Headset, Mail, Lock } from "lucide-react"

interface LoginFormProps {
  className?: string
}

export function LoginForm({ className }: LoginFormProps) {
  const router = useRouter()
  const { login } = useAuth()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      await login(email, password)
      router.push("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao fazer login")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={cn("flex flex-col items-center gap-6", className)}>
      {/* Logo e título animados */}
      <div className="flex flex-col items-center gap-3 animate-fade-in-down">
        <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse-slow" />
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/25 animate-float">
            <Headset className="h-8 w-8 text-primary-foreground" />
          </div>
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">Chama IA</h1>
          <p className="text-sm text-muted-foreground">Sistema de Chamados</p>
        </div>
      </div>

      {/* Card de login com animação */}
      <Card className="w-full animate-fade-in-up shadow-xl border-0 bg-card/80 backdrop-blur-sm">
        <CardHeader className="space-y-1 pb-4">
          <CardTitle className="text-xl text-center">Bem-vindo de volta</CardTitle>
          <CardDescription className="text-center">
            Entre com suas credenciais para acessar
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col gap-4">
              <div className="grid gap-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-10 h-11 transition-all duration-200 focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <div className="flex items-center">
                  <Label htmlFor="password" className="text-sm font-medium">
                    Senha
                  </Label>
                  <Link
                    href="/forgot-password"
                    className="ml-auto text-xs text-muted-foreground hover:text-primary transition-colors"
                  >
                    Esqueceu a senha?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pl-10 h-11 transition-all duration-200 focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-lg animate-shake">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                className="w-full h-11 mt-2 font-medium transition-all duration-200 hover:shadow-lg hover:shadow-primary/25 hover:-translate-y-0.5"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Entrando...
                  </>
                ) : (
                  "Entrar"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Footer */}
      <p className="text-xs text-muted-foreground animate-fade-in">
        Chama IA &copy; {new Date().getFullYear()}
      </p>
    </div>
  )
}
