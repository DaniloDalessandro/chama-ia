"use client"

import { Card, CardContent } from "@/components/ui/card"
import {
  FileText,
  Zap,
  Shield,
  BarChart3,
  Users,
  Clock,
  CheckCircle,
  TrendingUp
} from "lucide-react"

const features = [
  {
    icon: FileText,
    title: "Emissao de NF-e e NFS-e",
    description: "Emita notas fiscais eletronicas de produtos e servicos com apenas alguns cliques, 100% integrado com a SEFAZ.",
    color: "text-blue-500",
    bgColor: "bg-blue-500/10"
  },
  {
    icon: Zap,
    title: "Processos Automatizados",
    description: "Automatize a emissao recorrente, calculos de impostos e envio automatico por e-mail para seus clientes.",
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10"
  },
  {
    icon: Shield,
    title: "Seguranca e Conformidade",
    description: "Dados criptografados, backup automatico e total conformidade com a legislacao fiscal vigente.",
    color: "text-green-500",
    bgColor: "bg-green-500/10"
  },
  {
    icon: BarChart3,
    title: "Relatorios Inteligentes",
    description: "Dashboards completos com indicadores fiscais, financeiros e operacionais em tempo real.",
    color: "text-purple-500",
    bgColor: "bg-purple-500/10"
  },
  {
    icon: Users,
    title: "Gestao de Clientes",
    description: "Cadastro completo de clientes com historico de compras, notas emitidas e dados fiscais.",
    color: "text-orange-500",
    bgColor: "bg-orange-500/10"
  },
  {
    icon: Clock,
    title: "Suporte 24/7",
    description: "Equipe especializada disponivel para ajudar com duvidas fiscais e suporte tecnico.",
    color: "text-pink-500",
    bgColor: "bg-pink-500/10"
  }
]

const stats = [
  { value: "99.9%", label: "Uptime garantido" },
  { value: "-80%", label: "Reducao de erros" },
  { value: "5s", label: "Tempo medio de emissao" },
  { value: "24/7", label: "Suporte disponivel" }
]

export function AboutSection() {
  return (
    <section id="sobre" className="py-24 bg-background">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <span className="mb-4 inline-block rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
            Sobre o Sistema
          </span>
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Tudo que voce precisa para{" "}
            <span className="text-primary">gestao fiscal</span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Uma plataforma completa que automatiza a emissao de notas fiscais,
            reduz erros, centraliza informacoes e facilita a gestao do seu negocio.
          </p>
        </div>

        {/* Stats */}
        <div className="mb-16 grid grid-cols-2 gap-4 md:grid-cols-4">
          {stats.map((stat, index) => (
            <div
              key={index}
              className="flex flex-col items-center justify-center rounded-2xl border bg-card p-6 text-center shadow-sm"
            >
              <span className="mb-1 text-3xl font-bold text-primary md:text-4xl">
                {stat.value}
              </span>
              <span className="text-sm text-muted-foreground">{stat.label}</span>
            </div>
          ))}
        </div>

        {/* Feature Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <Card
                key={index}
                className="group relative overflow-hidden border-0 bg-gradient-to-br from-card to-card/50 shadow-md transition-all duration-300 hover:shadow-xl hover:-translate-y-1"
              >
                <CardContent className="p-6">
                  <div className={`mb-4 inline-flex rounded-xl ${feature.bgColor} p-3`}>
                    <Icon className={`h-6 w-6 ${feature.color}`} />
                  </div>
                  <h3 className="mb-2 text-xl font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  <p className="text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
                {/* Hover decoration */}
                <div className="absolute bottom-0 left-0 h-1 w-0 bg-gradient-to-r from-primary to-primary/50 transition-all duration-300 group-hover:w-full" />
              </Card>
            )
          })}
        </div>

        {/* Benefits list */}
        <div className="mt-16 rounded-2xl bg-gradient-to-br from-primary/5 to-primary/10 p-8 md:p-12">
          <div className="grid gap-8 md:grid-cols-2">
            <div>
              <h3 className="mb-4 text-2xl font-bold text-foreground">
                Por que escolher o ChamaNF?
              </h3>
              <p className="mb-6 text-muted-foreground">
                Desenvolvido por especialistas em tecnologia fiscal, nosso sistema
                atende todas as necessidades da sua empresa.
              </p>
              <div className="space-y-3">
                {[
                  "Interface intuitiva e facil de usar",
                  "Atualizacoes automaticas de legislacao",
                  "Integracao com ERPs e sistemas contabeis",
                  "Armazenamento seguro em nuvem"
                ].map((item, index) => (
                  <div key={index} className="flex items-center gap-3">
                    <CheckCircle className="h-5 w-5 flex-shrink-0 text-green-500" />
                    <span className="text-foreground">{item}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 blur-2xl" />
                <div className="relative rounded-2xl border bg-card p-6 shadow-lg">
                  <div className="flex items-center gap-4 mb-4">
                    <div className="rounded-full bg-green-500/10 p-2">
                      <TrendingUp className="h-6 w-6 text-green-500" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Economia mensal</p>
                      <p className="text-2xl font-bold text-foreground">R$ 2.500+</p>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Media de economia reportada por nossos clientes com automacao
                    e reducao de retrabalho.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
