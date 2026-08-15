"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import type { SensorReadings } from "@/types"

// Baseline values for CMAPSS sensors
const BASELINES: Record<string, number> = {
  T30: 1589.7,
  T50: 1400.6,
  Ps30: 47.54,
  phi: 521.66,
  BPR: 8.4195,
  W31: 38.81,
  W32: 23.42,
}

interface SensorReadingsChartProps {
  sensorReadings: SensorReadings
}

export default function SensorReadingsChart({ sensorReadings }: SensorReadingsChartProps) {
  const data = Object.entries(BASELINES)
    .filter(([key]) => sensorReadings[key] !== undefined)
    .map(([key, baseline]) => ({
      sensor: key,
      value: Number((sensorReadings[key] as number).toFixed(2)),
      baseline: baseline,
      deviation: Number((((sensorReadings[key] as number) - baseline) / baseline * 100).toFixed(1)),
    }))

  interface TooltipProps { active?: boolean; payload?: { payload: { value: number; baseline: number; deviation: number } }[]; label?: string }
  const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
    if (active && payload && payload.length) {
      const item = payload[0]?.payload
      return (
        <div className="bg-background border rounded-lg shadow p-3 text-xs">
          <p className="font-semibold">{label}</p>
          <p>Value: <span className="font-medium">{item?.value}</span></p>
          <p>Baseline: <span className="font-medium">{item?.baseline}</span></p>
          <p className={item?.deviation > 0 ? "text-red-600" : "text-green-600"}>
            Deviation: {item?.deviation > 0 ? "+" : ""}{item?.deviation}%
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
        <XAxis dataKey="sensor" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="deviation"
          fill="hsl(var(--primary))"
          name="Deviation %"
          radius={[3, 3, 0, 0]}
          label={false}
        />
        <ReferenceLine y={0} stroke="hsl(var(--border))" />
        <ReferenceLine y={5} stroke="hsl(var(--destructive))" strokeDasharray="4 4" strokeOpacity={0.7} />
        <ReferenceLine y={-5} stroke="hsl(var(--destructive))" strokeDasharray="4 4" strokeOpacity={0.7} />
      </BarChart>
    </ResponsiveContainer>
  )
}
