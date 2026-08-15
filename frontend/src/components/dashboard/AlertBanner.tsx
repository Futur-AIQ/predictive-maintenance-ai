"use client"

import { useState } from "react"
import Link from "next/link"
import { AlertTriangle, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { EquipmentListItem } from "@/types"

interface AlertBannerProps {
  criticalEquipment: EquipmentListItem[]
}

export default function AlertBanner({ criticalEquipment }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed || criticalEquipment.length === 0) return null

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
      <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-red-800">
          {criticalEquipment.length} Critical Equipment Alert{criticalEquipment.length > 1 ? "s" : ""}
        </p>
        <p className="text-sm text-red-700 mt-1">
          Immediate attention required:{" "}
          {criticalEquipment.map((e, i) => (
            <span key={e.equipment_id}>
              <Link
                href={`/dashboard/equipment/${e.equipment_id}`}
                className="font-medium underline hover:no-underline"
              >
                {e.equipment_id}
              </Link>
              {i < criticalEquipment.length - 1 ? ", " : ""}
            </span>
          ))}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 text-red-600 hover:bg-red-100 shrink-0"
        onClick={() => setDismissed(true)}
      >
        <X className="h-4 w-4" />
      </Button>
    </div>
  )
}
