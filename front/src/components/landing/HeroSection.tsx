"use client"

import { Button } from "@/components/ui/button"
import { FileText, MessageCircle, ArrowRight, Shield, Zap, CheckCircle } from "lucide-react"

interface HeroSectionProps {
  onOpenTicket: () => void
  onOpenChat: () => void
}

export function HeroSection({ onOpenTicket, onOpenChat }: HeroSectionProps) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-primary/5 via-background to-primary/10 pt-20 pb-32">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-80 w-80 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="container relative mx-auto px-4">
        <div className="mx-auto max-w-4xl text-center">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm font-medium text-primary">
            <Shield className="h-4 w-4" />
            Sistema homologado pela SEFAZ
          </div>

          {/* Logo/Name */}
          <h1 className="mb-4 text-4xl font-bold tracking-tight text-foreground md:text-5xl lg:text-6xl">
            Chama<span className="text-primary">NF</span>
          </h1>

          {/* Headline */}
          <h2 className="mb-6 text-2xl font-semibold text-foreground/90 md:text-3xl lg:text-4xl">
            Emita Notas Fiscais com{" "}
            <span className="bg-gradient-to-r from-primary to-primary/70 bg-clip-text text-transparent">
              rapidez, seguranca e sem burocracia
            </span>
          </h2>

          {/* Subtitle */}
          <p className="mx-auto mb-8 max-w-2xl text-lg text-muted-foreground md:text-xl">
            Solucao completa para emissao de NF-e e NFS-e, automacao de processos
            fiscais e conformidade tributaria. Simplifique a gestao do seu negocio.
          </p>

          {/* Features highlights */}
          <div className="mb-10 flex flex-wrap items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span>Emissao em segundos</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-500" />
              <span>Automacao completa</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              <span>100% seguro</span>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button
              size="lg"
              onClick={onOpenTicket}
              className="group h-12 px-8 text-base font-semibold shadow-lg shadow-primary/25 transition-all hover:shadow-xl hover:shadow-primary/30"
            >
              <FileText className="mr-2 h-5 w-5" />
              Abrir Chamado
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={onOpenChat}
              className="group h-12 px-8 text-base font-semibold"
            >
              <MessageCircle className="mr-2 h-5 w-5" />
              Falar com Atendimento
            </Button>
          </div>

          {/* Trust indicators */}
          <div className="mt-12 flex flex-col items-center gap-4">
            <p className="text-sm text-muted-foreground">
              Mais de <span className="font-semibold text-foreground">5.000 empresas</span> confiam em nosso sistema
            </p>
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <svg key={i} className="h-5 w-5 fill-yellow-400 text-yellow-400" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
              <span className="ml-2 text-sm font-medium text-foreground">4.9/5</span>
              <span className="text-sm text-muted-foreground">(2.847 avaliacoes)</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
