import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

const PUBLIC_ROUTES = ["/login", "/forgot-password", "/reset-password"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next()
  }

  const accessToken = request.cookies.get("access_token")?.value
  const refreshToken = request.cookies.get("refresh_token")?.value
  const hasTokens = accessToken || refreshToken

  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname.startsWith(route))

  if (pathname === "/") {
    return hasTokens
      ? NextResponse.redirect(new URL("/dashboard", request.url))
      : NextResponse.redirect(new URL("/login", request.url))
  }

  if (isPublicRoute && hasTokens) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  if (!isPublicRoute && !hasTokens) {
    return NextResponse.redirect(new URL("/login", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
}
