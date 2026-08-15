"use client"

import { useEffect, useState } from "react"
import { workOrderApi } from "@/lib/api"
import type { WorkOrderResponse } from "@/types"
import WorkOrderFilters from "@/components/workorders/WorkOrderFilters"
import WorkOrderTable from "@/components/workorders/WorkOrderTable"
import { Skeleton } from "@/components/ui/skeleton"

export default function WorkOrdersPage() {
  const [workOrders, setWorkOrders] = useState<WorkOrderResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState("ALL")
  const [severityFilter, setSeverityFilter] = useState("ALL")

  useEffect(() => {
    workOrderApi.list().then((data) => {
      setWorkOrders(data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleUpdate = (updated: WorkOrderResponse) => {
    setWorkOrders((prev) => prev.map((wo) => (wo.id === updated.id ? updated : wo)))
  }

  const handleDelete = (id: number) => {
    setWorkOrders((prev) => prev.filter((wo) => wo.id !== id))
  }

  const filtered = workOrders.filter((wo) => {
    const matchesStatus = statusFilter === "ALL" || wo.status === statusFilter
    const matchesSeverity = severityFilter === "ALL" || wo.severity === severityFilter
    return matchesStatus && matchesSeverity
  })

  return (
    <div className="space-y-4">
      <WorkOrderFilters
        statusFilter={statusFilter}
        severityFilter={severityFilter}
        onStatusChange={(v) => setStatusFilter(v)}
        onSeverityChange={(v) => setSeverityFilter(v)}
      />

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : (
        <WorkOrderTable
          workOrders={filtered}
          onUpdate={handleUpdate}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}
