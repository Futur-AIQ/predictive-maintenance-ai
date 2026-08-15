"use client"

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
  PolarRadiusAxis,
} from "recharts"
import type { EvaluationReport } from "@/types"

interface MetricsRadarChartProps {
  report: EvaluationReport
}

export default function MetricsRadarChart({ report }: MetricsRadarChartProps) {
  const data = [
    { metric: "Faithfulness", score: Math.round(report.faithfulness * 100), target: 75 },
    { metric: "Ans. Relevancy", score: Math.round(report.answer_relevancy * 100), target: 75 },
    { metric: "Ctx. Precision", score: Math.round(report.context_precision * 100), target: 75 },
    { metric: "Ctx. Recall", score: Math.round(report.context_recall * 100), target: 75 },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid />
        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Tooltip
          formatter={(value: number | undefined) => [`${value ?? 0}%`]}
        />
        <Radar
          name="Target"
          dataKey="target"
          stroke="hsl(var(--muted-foreground))"
          fill="hsl(var(--muted))"
          fillOpacity={0.3}
          strokeDasharray="4 4"
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="hsl(var(--primary))"
          fill="hsl(var(--primary))"
          fillOpacity={0.4}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
