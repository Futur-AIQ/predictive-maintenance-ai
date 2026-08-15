import { auth } from "@/lib/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const session = req.auth
  const isAuthenticated = !!session
  const pathname = req.nextUrl.pathname

  // Protect dashboard routes
  if (pathname.startsWith("/dashboard")) {
    if (!isAuthenticated) {
      return NextResponse.redirect(new URL("/login", req.url))
    }
    // Protect admin route
    if (pathname.startsWith("/dashboard/admin") && session.user.role !== "admin") {
      return NextResponse.redirect(new URL("/dashboard", req.url))
    }
  }

  // Redirect logged-in users away from login
  if (pathname === "/login" && isAuthenticated) {
    return NextResponse.redirect(new URL("/dashboard", req.url))
  }
})

export const config = {
  matcher: ["/dashboard/:path*", "/login"],
}
