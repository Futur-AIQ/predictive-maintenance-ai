"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Stethoscope } from "lucide-react"
import { equipmentApi } from "@/lib/api"
import type { HealthStatusResponse, SensorReadings } from "@/types"
import HealthStatusBadge from "@/components/equipment/HealthStatusBadge"
import SensorReadingsChart from "@/components/equipment/SensorReadingsChart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from "recharts"

export default function EquipmentDetailPage() {
  const params = useParams()
  const router = useRouter()
  const equipmentId = params.id as string

  const [health, setHealth] = useState<HealthStatusResponse | null>(null)
  const [sensors, setSensors] = useState<SensorReadings | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [h, s] = await Promise.all([
          equipmentApi.getHealth(equipmentId),
          equipmentApi.getSensors(equipmentId).catch(() => null),
        ])
        setHealth(h)
        setSensors(s || h.sensor_readings || null)
      } catch {
        router.push("/dashboard/equipment")
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [equipmentId, router])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!health) return null

  const rulPct = Math.min(100, (health.rul / 300) * 100)
  const rulData = [{ value: Math.round(rulPct), fill: rulPct < 20 ? "#ef4444" : rulPct < 50 ? "#f59e0b" : "#22c55e" }]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/equipment">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold">{health.equipment_id}</h1>
            <HealthStatusBadge status={health.status} />
          </div>
          <p className="text-sm text-muted-foreground capitalize">{health.equipment_type}</p>
        </div>
        <Button asChild>
          <Link href={`/dashboard/diagnostic?equipment_id=${health.equipment_id}`}>
            <Stethoscope className="mr-2 h-4 w-4" />
            Run Diagnostic
          </Link>
        </Button>
      </div>

      {/* Key metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Health Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{health.health_score.toFixed(1)}%</p>
            <Progress value={health.health_score} className="h-2 mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Remaining Useful Life</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-4">
            <div className="w-24 h-24">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  cx="50%" cy="50%"
                  innerRadius="60%" outerRadius="90%"
                  data={rulData}
                  startAngle={90} endAngle={-270}
                >
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={4} background />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="text-3xl font-bold">{Math.round(health.rul)}</p>
              <p className="text-sm text-muted-foreground">cycles</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Equipment Type</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold capitalize">{health.equipment_type}</p>
            <p className="text-sm text-muted-foreground mt-1">
              Status: <span className="font-medium">{health.status}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sensor Chart */}
      {sensors && Object.keys(sensors).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Sensor Readings vs Baseline (% Deviation)</CardTitle>
          </CardHeader>
          <CardContent>
            <SensorReadingsChart sensorReadings={sensors} />
            <p className="text-xs text-muted-foreground mt-2">
              Dashed lines indicate ±5% deviation threshold. Positive values indicate elevated readings.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Raw sensor values */}
      {sensors && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Raw Sensor Values</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {Object.entries(sensors)
                .filter(([, v]) => typeof v === "number" && !isNaN(v as number))
                .map(([key, value]) => (
                  <div key={key} className="bg-muted/50 rounded-md p-3">
                    <p className="text-xs text-muted-foreground">{key}</p>
                    <p className="text-sm font-semibold mt-0.5">{Number(value).toFixed(3)}</p>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
