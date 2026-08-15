"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useSession, signOut } from "next-auth/react"
import {
  LayoutDashboard,
  Stethoscope,
  Cog,
  ClipboardList,
  BarChart3,
  ShieldCheck,
  LogOut,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

const navLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/diagnostic", label: "Diagnostic", icon: Stethoscope },
  { href: "/dashboard/equipment", label: "Equipment", icon: Cog },
  { href: "/dashboard/workorders", label: "Work Orders", icon: ClipboardList },
  { href: "/dashboard/evaluation", label: "Evaluation", icon: BarChart3 },
]

const adminLink = { href: "/dashboard/admin", label: "Admin", icon: ShieldCheck }

interface MobileNavProps {
  open: boolean
  onClose: () => void
}

export default function MobileNav({ open, onClose }: MobileNavProps) {
  const pathname = usePathname()
  const { data: session } = useSession()

  const links = session?.user?.role === "admin" ? [...navLinks, adminLink] : navLinks

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="p-4 border-b">
          <SheetTitle className="flex items-center gap-2 text-left">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="Logo" className="w-7 h-7" />
            Predictive Maintenance AI
          </SheetTitle>
        </SheetHeader>

        <nav className="flex-1 py-4 space-y-1 px-3">
          {links.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href || (href !== "/dashboard" && pathname.startsWith(href))
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-5 w-5" />
                {label}
              </Link>
            )
          })}
        </nav>

        {session?.user && (
          <div className="border-t p-4 space-y-3">
            <div className="text-sm">
              <p className="font-medium">{session.user.name}</p>
              <p className="text-muted-foreground">{session.user.email}</p>
              <Badge variant="secondary" className="mt-1 capitalize">
                {session.user.role}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-start text-muted-foreground"
              onClick={() => signOut({ callbackUrl: "/login" })}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
