import Link from "next/link"
import { ArrowRight } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import HealthStatusBadge from "./HealthStatusBadge"
import type { EquipmentListItem } from "@/types"

interface EquipmentTableProps {
  equipment: EquipmentListItem[]
}

export default function EquipmentTable({ equipment }: EquipmentTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Equipment ID</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Health Score</TableHead>
            <TableHead className="hidden md:table-cell">RUL (cycles)</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {equipment.map((eq) => (
            <TableRow key={eq.equipment_id}>
              <TableCell className="font-medium">{eq.equipment_id}</TableCell>
              <TableCell className="capitalize text-muted-foreground">{eq.equipment_type}</TableCell>
              <TableCell>
                <HealthStatusBadge status={eq.status} />
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Progress value={eq.health_score} className="h-1.5 w-20" />
                  <span className="text-sm">{eq.health_score.toFixed(1)}%</span>
                </div>
              </TableCell>
              <TableCell className="hidden md:table-cell text-muted-foreground">
                {Math.round(eq.rul)}
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" asChild>
                  <Link href={`/dashboard/equipment/${eq.equipment_id}`}>
                    Details <ArrowRight className="ml-1 h-3 w-3" />
                  </Link>
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
