"use client"

import { useState } from "react"
import {
  Navbar,
  HeroSection,
  AboutSection,
  FeaturesSection,
  TicketForm,
  TrackingSection,
  ChatWidget,
  Footer
} from "@/components/landing"

export default function AtendimentoPage() {
  const [isChatOpen, setIsChatOpen] = useState(false)

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(sectionId)
    if (element) {
      element.scrollIntoView({ behavior: "smooth" })
    }
  }

  const handleOpenTicket = () => {
    scrollToSection("chamados")
  }

  const handleOpenChat = () => {
    setIsChatOpen(true)
  }

  return (
    <>
      <Navbar />

      <main>
        <HeroSection
          onOpenTicket={handleOpenTicket}
          onOpenChat={handleOpenChat}
        />

        <AboutSection />

        <FeaturesSection />

        <TicketForm />

        <TrackingSection />
      </main>

      <Footer />

      <ChatWidget isOpen={isChatOpen} onToggle={() => setIsChatOpen(!isChatOpen)} />
    </>
  )
}
