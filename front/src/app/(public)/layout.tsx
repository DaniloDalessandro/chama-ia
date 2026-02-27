import { Metadata } from "next"

export const metadata: Metadata = {
  title: "ChamaNF - Sistema de Emissao de Notas Fiscais",
  description: "Solucao completa para emissao de NF-e e NFS-e, automacao de processos fiscais e conformidade tributaria. Simplifique a gestao do seu negocio.",
  keywords: ["nota fiscal", "nf-e", "nfs-e", "emissao", "fiscal", "gestao", "empresarial"],
  openGraph: {
    title: "ChamaNF - Sistema de Emissao de Notas Fiscais",
    description: "Emita notas fiscais com rapidez, seguranca e sem burocracia.",
    type: "website",
  },
}

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-background">
      {children}
    </div>
  )
}
