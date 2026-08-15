import Link from "next/link"
import { ExternalLink } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import type { DiagnosticResponse } from "@/types"
import { cn } from "@/lib/utils"

const severityColors: Record<string, string> = {
  LOW: "bg-blue-100 text-blue-700 border-blue-200",
  MEDIUM: "bg-yellow-100 text-yellow-700 border-yellow-200",
  HIGH: "bg-orange-100 text-orange-700 border-orange-200",
  CRITICAL: "bg-red-100 text-red-700 border-red-200",
}

interface DiagnosticResultProps {
  result: DiagnosticResponse
}

export default function DiagnosticResult({ result }: DiagnosticResultProps) {
  const confidencePct = result.confidence_score != null ? Math.round(result.confidence_score * 100) : null
  const confidenceColor =
    confidencePct == null ? ""
    : confidencePct >= 80 ? "text-green-600"
    : confidencePct >= 60 ? "text-amber-600"
    : "text-red-600"

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Diagnostic Result</CardTitle>
          {result.severity && (
            <Badge
              className={cn("text-xs border", severityColors[result.severity] ?? "")}
              variant="outline"
            >
              {result.severity}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {result.diagnosis && (
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">Diagnosis</p>
            <p className="text-sm font-semibold">{result.diagnosis}</p>
          </div>
        )}

        {result.root_cause && (
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">Root Cause</p>
            <p className="text-sm">{result.root_cause}</p>
          </div>
        )}

        {result.recommended_action && (
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-1">
              Recommended Action
            </p>
            <p className="text-sm">{result.recommended_action}</p>
          </div>
        )}

        {confidencePct != null && (
          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-muted-foreground">Confidence</span>
              <span className={cn("font-medium", confidenceColor)}>{confidencePct}%</span>
            </div>
            <Progress value={confidencePct} className="h-2" />
          </div>
        )}

        {result.work_order_id && (
          <div className="pt-1">
            <Link
              href="/dashboard/workorders"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Work Order #{result.work_order_id} created
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
