import { Activity, AlertTriangle, ClipboardList, Heart } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { EquipmentListItem, WorkOrderResponse } from "@/types"
import { cn } from "@/lib/utils"

interface StatsOverviewProps {
  equipment: EquipmentListItem[]
  workOrders: WorkOrderResponse[]
}

export default function StatsOverview({ equipment, workOrders }: StatsOverviewProps) {
  const totalEquipment = equipment.length
  const criticalCount = equipment.filter((e) => e.status === "CRITICAL").length
  const openWorkOrders = workOrders.filter((w) => w.status === "OPEN").length
  const avgHealth =
    equipment.length > 0
      ? Math.round(equipment.reduce((sum, e) => sum + e.health_score, 0) / equipment.length)
      : 0

  const stats = [
    {
      title: "Total Equipment",
      value: totalEquipment,
      icon: Activity,
      description: "Monitored assets",
      color: "text-blue-600",
    },
    {
      title: "Critical Alerts",
      value: criticalCount,
      icon: AlertTriangle,
      description: "Require immediate attention",
      color: criticalCount > 0 ? "text-red-600" : "text-green-600",
    },
    {
      title: "Open Work Orders",
      value: openWorkOrders,
      icon: ClipboardList,
      description: "Pending resolution",
      color: openWorkOrders > 0 ? "text-amber-600" : "text-green-600",
    },
    {
      title: "Avg Health Score",
      value: `${avgHealth}%`,
      icon: Heart,
      description: "Fleet health index",
      color: avgHealth >= 70 ? "text-green-600" : avgHealth >= 50 ? "text-amber-600" : "text-red-600",
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
            <stat.icon className={cn("h-5 w-5", stat.color)} />
          </CardHeader>
          <CardContent>
            <div className={cn("text-2xl font-bold", stat.color)}>{stat.value}</div>
            <p className="text-xs text-muted-foreground mt-1">{stat.description}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
