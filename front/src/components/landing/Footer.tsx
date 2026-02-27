"use client"

import Link from "next/link"
import {
  FileText,
  Mail,
  Phone,
  MapPin,
  Linkedin,
  Twitter,
  Instagram,
  Facebook
} from "lucide-react"

const footerLinks = {
  produto: [
    { label: "Funcionalidades", href: "#funcionalidades" },
    { label: "Precos", href: "#precos" },
    { label: "Integracoes", href: "#integracoes" },
    { label: "Atualizacoes", href: "#atualizacoes" }
  ],
  suporte: [
    { label: "Central de Ajuda", href: "#ajuda" },
    { label: "Abrir Chamado", href: "#chamados" },
    { label: "Status do Sistema", href: "#status" },
    { label: "Documentacao", href: "#docs" }
  ],
  empresa: [
    { label: "Sobre Nos", href: "#sobre" },
    { label: "Blog", href: "#blog" },
    { label: "Carreiras", href: "#carreiras" },
    { label: "Contato", href: "#contato" }
  ],
  legal: [
    { label: "Termos de Uso", href: "/termos" },
    { label: "Politica de Privacidade", href: "/privacidade" },
    { label: "LGPD", href: "/lgpd" },
    { label: "Cookies", href: "/cookies" }
  ]
}

const socialLinks = [
  { icon: Linkedin, href: "#", label: "LinkedIn" },
  { icon: Twitter, href: "#", label: "Twitter" },
  { icon: Instagram, href: "#", label: "Instagram" },
  { icon: Facebook, href: "#", label: "Facebook" }
]

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="container mx-auto px-4">
        {/* Main Footer */}
        <div className="grid gap-8 py-12 md:grid-cols-2 lg:grid-cols-6">
          {/* Brand Column */}
          <div className="lg:col-span-2">
            <Link href="/" className="mb-4 inline-flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <FileText className="h-5 w-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">
                Chama<span className="text-primary">NF</span>
              </span>
            </Link>
            <p className="mb-6 text-sm text-muted-foreground max-w-xs">
              Solucao completa para emissao de notas fiscais eletronicas,
              gestao fiscal e automacao de processos para sua empresa.
            </p>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                <a href="mailto:contato@chamanf.com.br" className="hover:text-foreground">
                  contato@chamanf.com.br
                </a>
              </div>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4" />
                <a href="tel:+551140028922" className="hover:text-foreground">
                  (11) 4002-8922
                </a>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                <span>Sao Paulo, SP - Brasil</span>
              </div>
            </div>
          </div>

          {/* Links Columns */}
          <div>
            <h4 className="mb-4 font-semibold text-foreground">Produto</h4>
            <ul className="space-y-2">
              {footerLinks.produto.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-foreground">Suporte</h4>
            <ul className="space-y-2">
              {footerLinks.suporte.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-foreground">Empresa</h4>
            <ul className="space-y-2">
              {footerLinks.empresa.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-4 font-semibold text-foreground">Legal</h4>
            <ul className="space-y-2">
              {footerLinks.legal.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Footer */}
        <div className="flex flex-col items-center justify-between gap-4 border-t py-6 md:flex-row">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} ChamaNF. Todos os direitos reservados.
          </p>

          {/* Social Links */}
          <div className="flex items-center gap-4">
            {socialLinks.map((social) => {
              const Icon = social.icon
              return (
                <a
                  key={social.label}
                  href={social.href}
                  aria-label={social.label}
                  className="flex h-9 w-9 items-center justify-center rounded-full bg-muted text-muted-foreground transition-colors hover:bg-primary hover:text-primary-foreground"
                >
                  <Icon className="h-4 w-4" />
                </a>
              )
            })}
          </div>
        </div>
      </div>
    </footer>
  )
}
