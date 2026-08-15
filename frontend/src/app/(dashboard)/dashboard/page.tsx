"use client"

import { useEffect, useState } from "react"
import { equipmentApi, workOrderApi } from "@/lib/api"
import type { EquipmentListItem, WorkOrderResponse } from "@/types"
import StatsOverview from "@/components/dashboard/StatsOverview"
import EquipmentHealthCard from "@/components/dashboard/EquipmentHealthCard"
import AlertBanner from "@/components/dashboard/AlertBanner"
import RecentWorkOrders from "@/components/dashboard/RecentWorkOrders"
import { Skeleton } from "@/components/ui/skeleton"

export default function DashboardPage() {
  const [equipment, setEquipment] = useState<EquipmentListItem[]>([])
  const [workOrders, setWorkOrders] = useState<WorkOrderResponse[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [eq, wo] = await Promise.all([
          equipmentApi.list(),
          workOrderApi.list({ size: 5 }),
        ])
        // Sort by criticality: CRITICAL first, then WARNING, then OK
        const sorted = [...eq].sort((a, b) => {
          const order = { CRITICAL: 0, WARNING: 1, OK: 2 }
          return order[a.status] - order[b.status]
        })
        setEquipment(sorted)
        setWorkOrders(wo)
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  const criticalEquipment = equipment.filter((e) => e.status === "CRITICAL")
  const topEquipment = equipment.slice(0, 8)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <AlertBanner criticalEquipment={criticalEquipment} />
      <StatsOverview equipment={equipment} workOrders={workOrders} />

      <div>
        <h2 className="text-sm font-semibold text-muted-foreground mb-3">
          Equipment Health Overview (Top 8 by Priority)
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {topEquipment.map((eq) => (
            <EquipmentHealthCard key={eq.equipment_id} equipment={eq} />
          ))}
        </div>
      </div>

      <RecentWorkOrders workOrders={workOrders} />
    </div>
  )
}
