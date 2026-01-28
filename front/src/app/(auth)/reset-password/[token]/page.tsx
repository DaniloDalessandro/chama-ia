"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
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
import { ArrowLeft, Loader2, CheckCircle } from "lucide-react"

export default function ResetPasswordPage() {
  const params = useParams()
  const router = useRouter()
  const token = params.token as string

  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (password !== confirmPassword) {
      setError("As senhas não coincidem")
      return
    }

    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres")
      return
    }

    setIsLoading(true)

    try {
      const response = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.message || "Erro ao redefinir senha")
      }

      setIsSuccess(true)
      setTimeout(() => {
        router.push("/login")
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao processar solicitação")
    } finally {
      setIsLoading(false)
    }
  }

  if (isSuccess) {
    return (
      <div className={cn("flex flex-col gap-6")}>
        <Card>
          <CardHeader className="text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <CardTitle>Senha redefinida!</CardTitle>
            <CardDescription>
              Sua senha foi alterada com sucesso. Você será redirecionado para o
              login em instantes...
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/login">
              <Button className="w-full">Ir para o login</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6")}>
      <Card>
        <CardHeader>
          <CardTitle>Redefinir senha</CardTitle>
          <CardDescription>
            Digite sua nova senha abaixo.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col gap-4">
              <div className="grid gap-2">
                <Label htmlFor="password">Nova senha</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                  minLength={8}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="confirmPassword">Confirmar senha</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={isLoading}
                  minLength={8}
                />
              </div>

              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Redefinir senha
              </Button>

              <Link href="/login">
                <Button variant="ghost" className="w-full">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Voltar para o login
                </Button>
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
