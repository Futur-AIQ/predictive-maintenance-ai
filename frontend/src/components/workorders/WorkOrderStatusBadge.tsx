import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { WorkOrderStatus } from "@/types"

const config: Record<WorkOrderStatus, { label: string; className: string }> = {
  OPEN: { label: "Open", className: "bg-blue-100 text-blue-700 border-blue-200" },
  IN_PROGRESS: { label: "In Progress", className: "bg-yellow-100 text-yellow-700 border-yellow-200" },
  RESOLVED: { label: "Resolved", className: "bg-green-100 text-green-700 border-green-200" },
  CLOSED: { label: "Closed", className: "bg-gray-100 text-gray-700 border-gray-200" },
}

interface WorkOrderStatusBadgeProps {
  status: WorkOrderStatus
  className?: string
}

export default function WorkOrderStatusBadge({ status, className }: WorkOrderStatusBadgeProps) {
  const { label, className: colorClass } = config[status] || config.OPEN
  return (
    <Badge className={cn("border", colorClass, className)} variant="outline">
      {label}
    </Badge>
  )
}
