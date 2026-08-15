import Link from "next/link"
import { format } from "date-fns"
import { ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { WorkOrderResponse } from "@/types"
import { cn } from "@/lib/utils"

const severityColors: Record<string, string> = {
  LOW: "bg-blue-100 text-blue-700 border-blue-200",
  MEDIUM: "bg-yellow-100 text-yellow-700 border-yellow-200",
  HIGH: "bg-orange-100 text-orange-700 border-orange-200",
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
}

const statusColors: Record<string, string> = {
  OPEN: "bg-blue-100 text-blue-700 border-blue-200",
  IN_PROGRESS: "bg-yellow-100 text-yellow-700 border-yellow-200",
  RESOLVED: "bg-green-100 text-green-700 border-green-200",
  CLOSED: "bg-gray-100 text-gray-700 border-gray-200",
}

interface RecentWorkOrdersProps {
  workOrders: WorkOrderResponse[]
}

export default function RecentWorkOrders({ workOrders }: RecentWorkOrdersProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Recent Work Orders</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/dashboard/workorders" className="flex items-center gap-1">
            View All <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {workOrders.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">No work orders found</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Equipment</TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden sm:table-cell">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {workOrders.slice(0, 5).map((wo) => (
                <TableRow key={wo.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/dashboard/equipment/${wo.equipment_id}`}
                      className="hover:underline text-sm"
                    >
                      {wo.equipment_id}
                    </Link>
                    <p className="text-xs text-muted-foreground truncate max-w-[140px]">
                      {wo.fault_description}
                    </p>
                  </TableCell>
                  <TableCell>
                    <Badge className={cn("text-xs border", severityColors[wo.severity])} variant="outline">
                      {wo.severity}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={cn("text-xs border", statusColors[wo.status])} variant="outline">
                      {wo.status.replace("_", " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="hidden sm:table-cell text-sm text-muted-foreground">
                    {format(new Date(wo.created_at), "MMM d, yyyy")}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
