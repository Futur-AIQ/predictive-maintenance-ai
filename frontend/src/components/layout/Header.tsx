"use client"

import { usePathname } from "next/navigation"
import { useSession } from "next-auth/react"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

const routeTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/dashboard/diagnostic": "AI Diagnostic",
  "/dashboard/equipment": "Equipment",
  "/dashboard/workorders": "Work Orders",
  "/dashboard/evaluation": "RAG Evaluation",
  "/dashboard/admin": "Admin Panel",
}

interface HeaderProps {
  onMenuClick: () => void
}

export default function Header({ onMenuClick }: HeaderProps) {
  const pathname = usePathname()
  const { data: session } = useSession()

  const title =
    Object.entries(routeTitles).find(([key]) => pathname === key || pathname.startsWith(key + "/"))?.[1] ||
    "Dashboard"

  const initials = session?.user?.name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "U"

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background px-4 md:px-6">
      <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
        <Menu className="h-5 w-5" />
      </Button>
      <h1 className="text-lg font-semibold flex-1">{title}</h1>
      <div className="flex items-center gap-3">
        {session?.user && (
          <>
            <span className="text-sm text-muted-foreground hidden sm:block">{session.user.name}</span>
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
          </>
        )}
      </div>
    </header>
  )
}
