"use client"

import { useEffect, useState } from "react"
import { useSession } from "next-auth/react"
import { format } from "date-fns"
import { Loader2, PlayCircle } from "lucide-react"
import { evaluationApi } from "@/lib/api"
import type { EvaluationReport } from "@/types"
import MetricsGrid from "@/components/evaluation/MetricsGrid"
import MetricsRadarChart from "@/components/evaluation/MetricsRadarChart"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

function overallScore(report: EvaluationReport): number {
  return (
    report.faithfulness +
    report.answer_relevancy +
    report.context_precision +
    report.context_recall
  ) / 4
}

function getInterpretation(score: number): string {
  if (score >= 0.85) return "Excellent RAG performance. The system demonstrates high accuracy and relevance."
  if (score >= 0.70) return "Good RAG performance. Minor improvements may enhance context precision."
  if (score >= 0.55) return "Moderate performance. Consider expanding the knowledge base or improving retrieval."
  return "Below target performance. Review document quality and embedding configuration."
}

export default function EvaluationPage() {
  const { data: session } = useSession()
  const isAdmin = session?.user?.role === "admin"
  const [report, setReport] = useState<EvaluationReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    evaluationApi.latest().then(setReport).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleRun = async () => {
    setRunning(true)
    try {
      const result = await evaluationApi.run()
      setReport(result)
      toast.success("Evaluation complete!")
    } catch {
      toast.error("Evaluation failed. Please try again.")
    } finally {
      setRunning(false)
    }
  }

  const overall = report ? overallScore(report) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm text-muted-foreground">RAG Pipeline Performance</h2>
          {report && (
            <p className="text-xs text-muted-foreground mt-0.5">
              Last evaluated: {format(new Date(report.timestamp), "MMM d, yyyy HH:mm")}
              {report.sample_count > 0 && ` · ${report.sample_count} samples`}
            </p>
          )}
        </div>
        <Button
          onClick={handleRun}
          disabled={running || !isAdmin}
          title={!isAdmin ? "Admin access required" : undefined}
        >
          {running ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Running...</>
          ) : (
            <><PlayCircle className="mr-2 h-4 w-4" />Run Evaluation</>
          )}
        </Button>
      </div>

      {loading ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-36" />)}
          </div>
          <Skeleton className="h-72" />
        </div>
      ) : report ? (
        <>
          <MetricsGrid report={report} />

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Metrics Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <MetricsRadarChart report={report} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Analysis</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium mb-1">Overall Score</p>
                  <p className={cn(
                    "text-4xl font-bold",
                    overall >= 0.8 ? "text-green-600" :
                    overall >= 0.6 ? "text-amber-600" : "text-red-600"
                  )}>
                    {Math.round(overall * 100)}%
                  </p>
                </div>
                <p className="text-sm text-muted-foreground">{getInterpretation(overall)}</p>
              </CardContent>
            </Card>
          </div>
        </>
      ) : (
        <Card>
          <CardContent className="py-16 text-center">
            <p className="text-muted-foreground text-sm">No evaluation report available.</p>
            {isAdmin && (
              <Button onClick={handleRun} disabled={running} className="mt-4">
                Run First Evaluation
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
