"use client"

import { useState } from "react"
import Link from "next/link"
import { format } from "date-fns"
import { Trash2 } from "lucide-react"
import { useSession } from "next-auth/react"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import WorkOrderStatusBadge from "./WorkOrderStatusBadge"
import { workOrderApi } from "@/lib/api"
import type { WorkOrderResponse, WorkOrderStatus, Severity } from "@/types"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

const severityColors: Record<Severity, string> = {
  LOW: "bg-blue-100 text-blue-700 border-blue-200",
  MEDIUM: "bg-yellow-100 text-yellow-700 border-yellow-200",
  HIGH: "bg-orange-100 text-orange-700 border-orange-200",
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
}

interface WorkOrderTableProps {
  workOrders: WorkOrderResponse[]
  onUpdate: (updated: WorkOrderResponse) => void
  onDelete: (id: number) => void
}

export default function WorkOrderTable({ workOrders, onUpdate, onDelete }: WorkOrderTableProps) {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const [updatingId, setUpdatingId] = useState<number | null>(null)

  const handleStatusChange = async (id: number, status: WorkOrderStatus) => {
    setUpdatingId(id)
    try {
      const updated = await workOrderApi.updateStatus(id, { status })
      onUpdate(updated)
      toast.success("Status updated")
    } catch {
      toast.error("Failed to update status")
    } finally {
      setUpdatingId(null)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this work order?")) return
    try {
      await workOrderApi.delete(id)
      onDelete(id)
      toast.success("Work order deleted")
    } catch {
      toast.error("Failed to delete work order")
    }
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>WO #</TableHead>
            <TableHead>Equipment</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="hidden md:table-cell">Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {workOrders.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No work orders found
              </TableCell>
            </TableRow>
          ) : (
            workOrders.map((wo) => (
              <TableRow key={wo.id}>
                <TableCell className="font-medium text-muted-foreground">#{wo.id}</TableCell>
                <TableCell>
                  <Link href={`/dashboard/equipment/${wo.equipment_id}`} className="hover:underline font-medium">
                    {wo.equipment_id}
                  </Link>
                </TableCell>
                <TableCell>
                  <Badge className={cn("text-xs border", severityColors[wo.severity])} variant="outline">
                    {wo.severity}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Select
                    value={wo.status}
                    onValueChange={(v) => handleStatusChange(wo.id, v as WorkOrderStatus)}
                    disabled={updatingId === wo.id}
                  >
                    <SelectTrigger className="h-7 text-xs w-32 border-0 p-0">
                      <SelectValue>
                        <WorkOrderStatusBadge status={wo.status} />
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="OPEN">Open</SelectItem>
                      <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
                      <SelectItem value="RESOLVED">Resolved</SelectItem>
                      <SelectItem value="CLOSED">Closed</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell className="hidden md:table-cell text-sm text-muted-foreground">
                  {format(new Date(wo.created_at), "MMM d, yyyy")}
                </TableCell>
                <TableCell className="text-right">
                  {isAdmin && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(wo.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
