"use client"

import { usePathname } from "next/navigation"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { ThemeToggle } from "@/components/common/ThemeToggle"

const routeNames: Record<string, string> = {
  dashboard: "Dashboard",
  usuarios: "Usuários",
  configuracoes: "Configurações",
}

export function Header() {
  const pathname = usePathname()
  const pathSegments = pathname.split("/").filter(Boolean)

  const breadcrumbItems = pathSegments.map((segment, index) => {
    const path = "/" + pathSegments.slice(0, index + 1).join("/")
    const name = routeNames[segment] || segment.charAt(0).toUpperCase() + segment.slice(1)
    const isLast = index === pathSegments.length - 1

    return { path, name, isLast }
  })

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />

      <Breadcrumb>
        <BreadcrumbList>
          {breadcrumbItems.map((item, index) => (
            <BreadcrumbItem key={item.path}>
              {index > 0 && <BreadcrumbSeparator />}
              {item.isLast ? (
                <BreadcrumbPage>{item.name}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink href={item.path}>{item.name}</BreadcrumbLink>
              )}
            </BreadcrumbItem>
          ))}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="ml-auto">
        <ThemeToggle />
      </div>
    </header>
  )
}
