"use client"

import {
  FileText,
  XCircle,
  Users,
  Package,
  Calculator,
  FileBarChart,
  History,
  Plug,
  Headphones,
  ArrowRight
} from "lucide-react"

const features = [
  {
    icon: FileText,
    title: "Emissao de Notas Fiscais",
    description: "Emita NF-e e NFS-e de forma rapida e simplificada, com calculo automatico de impostos."
  },
  {
    icon: XCircle,
    title: "Cancelamento de Notas",
    description: "Cancele notas fiscais dentro do prazo legal com apenas alguns cliques."
  },
  {
    icon: Users,
    title: "Cadastro de Clientes",
    description: "Gerencie seus clientes com dados completos, CNPJ/CPF e endereco para emissao."
  },
  {
    icon: Package,
    title: "Cadastro de Produtos",
    description: "Catalogo de produtos com NCM, CFOP, unidades e precos pre-configurados."
  },
  {
    icon: Calculator,
    title: "Gestao de Impostos",
    description: "Calculos automaticos de ICMS, IPI, PIS, COFINS, ISS e demais tributos."
  },
  {
    icon: FileBarChart,
    title: "Relatorios Fiscais",
    description: "Relatorios completos para fechamento mensal, SPED e obrigacoes acessorias."
  },
  {
    icon: History,
    title: "Historico de Notas",
    description: "Consulte todas as notas emitidas, canceladas ou inutilizadas em um so lugar."
  },
  {
    icon: Plug,
    title: "Integracoes",
    description: "Conecte com ERPs, marketplaces, gateways de pagamento e sistemas contabeis."
  },
  {
    icon: Headphones,
    title: "Suporte Integrado",
    description: "Atendimento especializado para duvidas fiscais e suporte tecnico."
  }
]

export function FeaturesSection() {
  return (
    <section id="funcionalidades" className="py-24 bg-muted/30">
      <div className="container mx-auto px-4">
        {/* Section Header */}
        <div className="mx-auto max-w-3xl text-center mb-16">
          <span className="mb-4 inline-block rounded-full bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
            Funcionalidades
          </span>
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            Recursos completos para sua{" "}
            <span className="text-primary">gestao fiscal</span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Do cadastro a emissao, tudo integrado em uma unica plataforma
            pensada para simplificar o dia a dia da sua empresa.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => {
            const Icon = feature.icon
            return (
              <div
                key={index}
                className="group flex gap-4 rounded-xl border bg-card p-5 shadow-sm transition-all duration-300 hover:border-primary/50 hover:shadow-md"
              >
                <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <Icon className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="mb-1 font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {/* CTA */}
        <div className="mt-16 text-center">
          <div className="inline-flex flex-col items-center rounded-2xl border bg-card p-8 shadow-sm">
            <h3 className="mb-2 text-xl font-semibold text-foreground">
              Ainda tem duvidas?
            </h3>
            <p className="mb-4 text-muted-foreground">
              Nossa equipe esta pronta para ajudar voce a encontrar a melhor solucao.
            </p>
            <a
              href="#chamados"
              className="group inline-flex items-center gap-2 font-medium text-primary hover:underline"
            >
              Fale com um especialista
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
