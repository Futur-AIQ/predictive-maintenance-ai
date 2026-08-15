import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { HealthStatus } from "@/types"

const config: Record<HealthStatus, { label: string; className: string }> = {
  CRITICAL: { label: "Critical", className: "bg-red-100 text-red-700 border-red-200" },
  WARNING: { label: "Warning", className: "bg-amber-100 text-amber-700 border-amber-200" },
  OK: { label: "OK", className: "bg-green-100 text-green-700 border-green-200" },
}

interface HealthStatusBadgeProps {
  status: HealthStatus
  className?: string
}

export default function HealthStatusBadge({ status, className }: HealthStatusBadgeProps) {
  const { label, className: colorClass } = config[status] || config.OK
  return (
    <Badge className={cn("border", colorClass, className)} variant="outline">
      {label}
    </Badge>
  )
}
