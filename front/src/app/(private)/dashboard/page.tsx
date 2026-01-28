"use client"

import { useAuth } from "@/hooks/useAuth"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Activity, CreditCard, Users, DollarSign } from "lucide-react"

export default function DashboardPage() {
  const { user } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Bem-vindo de volta{user?.name ? `, ${user.name}` : ""}!
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Receita Total
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">R$ 45.231,89</div>
            <p className="text-xs text-muted-foreground">
              +20.1% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Assinaturas
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+2.350</div>
            <p className="text-xs text-muted-foreground">
              +180 desde a última semana
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Vendas</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+12.234</div>
            <p className="text-xs text-muted-foreground">
              +19% em relação ao mês anterior
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ativos Agora</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">+573</div>
            <p className="text-xs text-muted-foreground">
              +201 na última hora
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle>Visão Geral</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            <div className="h-[350px] flex items-center justify-center text-muted-foreground">
              Gráfico de visão geral
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Vendas Recentes</CardTitle>
            <CardDescription>
              Você fez 265 vendas este mês.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-8">
              {[
                { name: "Olivia Martin", email: "olivia.martin@email.com", amount: "+R$ 1.999,00" },
                { name: "Jackson Lee", email: "jackson.lee@email.com", amount: "+R$ 39,00" },
                { name: "Isabella Nguyen", email: "isabella.nguyen@email.com", amount: "+R$ 299,00" },
                { name: "William Kim", email: "will@email.com", amount: "+R$ 99,00" },
                { name: "Sofia Davis", email: "sofia.davis@email.com", amount: "+R$ 39,00" },
              ].map((sale, index) => (
                <div key={index} className="flex items-center">
                  <div className="h-9 w-9 rounded-full bg-muted flex items-center justify-center">
                    <span className="text-sm font-medium">
                      {sale.name.split(" ").map(n => n[0]).join("")}
                    </span>
                  </div>
                  <div className="ml-4 space-y-1">
                    <p className="text-sm font-medium leading-none">{sale.name}</p>
                    <p className="text-sm text-muted-foreground">{sale.email}</p>
                  </div>
                  <div className="ml-auto font-medium">{sale.amount}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
