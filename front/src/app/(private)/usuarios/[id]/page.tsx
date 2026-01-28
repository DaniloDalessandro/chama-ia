"use client"

import { useParams } from "next/navigation"
import Link from "next/link"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Edit, Trash2, Mail, User, Shield, Calendar } from "lucide-react"

const mockUsers: Record<string, {
  id: string
  name: string
  email: string
  role: string
  status: string
  createdAt: string
  lastLogin: string
}> = {
  "1": { id: "1", name: "João Silva", email: "joao@email.com", role: "Admin", status: "Ativo", createdAt: "2024-01-15", lastLogin: "2024-12-20" },
  "2": { id: "2", name: "Maria Santos", email: "maria@email.com", role: "Usuário", status: "Ativo", createdAt: "2024-02-20", lastLogin: "2024-12-19" },
  "3": { id: "3", name: "Pedro Oliveira", email: "pedro@email.com", role: "Usuário", status: "Inativo", createdAt: "2024-03-10", lastLogin: "2024-11-05" },
  "4": { id: "4", name: "Ana Costa", email: "ana@email.com", role: "Editor", status: "Ativo", createdAt: "2024-04-05", lastLogin: "2024-12-18" },
  "5": { id: "5", name: "Carlos Souza", email: "carlos@email.com", role: "Usuário", status: "Ativo", createdAt: "2024-05-12", lastLogin: "2024-12-20" },
}

export default function UsuarioDetalhesPage() {
  const params = useParams()
  const userId = params.id as string
  const user = mockUsers[userId]

  if (!user) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <Link href="/usuarios">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Usuário não encontrado</h1>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/usuarios">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{user.name}</h1>
            <p className="text-muted-foreground">
              Detalhes do usuário
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Edit className="mr-2 h-4 w-4" />
            Editar
          </Button>
          <Button variant="destructive">
            <Trash2 className="mr-2 h-4 w-4" />
            Excluir
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Informações Pessoais</CardTitle>
            <CardDescription>
              Dados do perfil do usuário.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <User className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Nome</p>
                <p className="font-medium">{user.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium">{user.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Função</p>
                <p className="font-medium">{user.role}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status da Conta</CardTitle>
            <CardDescription>
              Informações sobre a conta do usuário.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-4 w-4" />
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <Badge
                  variant={user.status === "Ativo" ? "default" : "secondary"}
                >
                  {user.status}
                </Badge>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Data de Criação</p>
                <p className="font-medium">
                  {new Date(user.createdAt).toLocaleDateString("pt-BR")}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm text-muted-foreground">Último Acesso</p>
                <p className="font-medium">
                  {new Date(user.lastLogin).toLocaleDateString("pt-BR")}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
