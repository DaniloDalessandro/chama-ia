"use client"

import { AuthGuard } from "@/components/auth/AuthGuard"
import { DataRefreshProvider } from "@/context/DataRefreshContext"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { Header } from "@/components/layout/Header"

export default function PrivateLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard>
      <DataRefreshProvider>
        <SidebarProvider>
          <AppSidebar />
          <SidebarInset>
            <Header />
            <main className="flex-1 p-6">
              {children}
            </main>
          </SidebarInset>
        </SidebarProvider>
      </DataRefreshProvider>
    </AuthGuard>
  )
}
