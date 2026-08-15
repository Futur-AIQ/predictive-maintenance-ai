import Link from "next/link"
import { Cog, Droplets, Zap } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import type { EquipmentListItem } from "@/types"

const statusConfig = {
  CRITICAL: { label: "Critical", className: "bg-red-100 text-red-700 border-red-200" },
  WARNING: { label: "Warning", className: "bg-amber-100 text-amber-700 border-amber-200" },
  OK: { label: "OK", className: "bg-green-100 text-green-700 border-green-200" },
}

const typeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  turbofan: Cog,
  pump: Droplets,
  compressor: Zap,
}

interface EquipmentHealthCardProps {
  equipment: EquipmentListItem
}

export default function EquipmentHealthCard({ equipment }: EquipmentHealthCardProps) {
  const status = statusConfig[equipment.status]
  const Icon = typeIcons[equipment.equipment_type] || Cog

  return (
    <Link href={`/dashboard/equipment/${equipment.equipment_id}`}>
      <Card className={cn(
        "hover:shadow-md transition-shadow cursor-pointer border-l-4",
        equipment.status === "CRITICAL" && "border-l-red-500",
        equipment.status === "WARNING" && "border-l-amber-500",
        equipment.status === "OK" && "border-l-green-500",
      )}>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icon className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium text-sm">{equipment.equipment_id}</span>
            </div>
            <Badge className={cn("text-xs border", status.className)} variant="outline">
              {status.label}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground capitalize">{equipment.equipment_type}</p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">Health Score</span>
              <span className="font-medium">{equipment.health_score.toFixed(1)}%</span>
            </div>
            <Progress
              value={equipment.health_score}
              className="h-2"
            />
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">RUL</span>
            <span className="font-medium">{Math.round(equipment.rul)} cycles</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  )
}
