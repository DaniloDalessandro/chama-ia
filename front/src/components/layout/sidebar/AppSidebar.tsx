"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Headset, Home, Users, Settings, ExternalLink, Ticket, History, Building2 } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { NavMain } from "@/components/layout/navigation/NavMain"
import { NavSecondary } from "@/components/layout/navigation/NavSecondary"
import { NavUser } from "@/components/layout/navigation/NavUser"
import { useAuth } from "@/hooks/useAuth"

const navItems = [
  {
    title: "Dashboard",
    url: "/dashboard",
    icon: Home,
  },
  {
    title: "Chamados",
    url: "/chamados",
    icon: Ticket,
  },
  {
    title: "Histórico",
    url: "/historico",
    icon: History,
  },
  {
    title: "Clientes",
    url: "/clientes",
    icon: Building2,
  },
  {
    title: "Usuários",
    url: "/usuarios",
    icon: Users,
  },
  {
    title: "Configurações",
    url: "/configuracoes",
    icon: Settings,
  },
  {
    title: "Landing Page",
    url: "/atendimento",
    icon: ExternalLink,
    external: true,
  },
]

const navSecondary: { title: string; url: string; icon: typeof Home; external?: boolean }[] = []

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()
  const { user } = useAuth()

  return (
    <Sidebar variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link href="/dashboard">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <Headset className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">Chama IA</span>
                  <span className="truncate text-xs">Plataforma</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <NavMain items={navItems} pathname={pathname} />
        <NavSecondary items={navSecondary} className="mt-auto" />
      </SidebarContent>

      <SidebarFooter>
        <NavUser
          user={{
            name: user?.name || "Usuário",
            email: user?.email || "usuario@email.com",
            avatar: "",
          }}
        />
      </SidebarFooter>
    </Sidebar>
  )
}
