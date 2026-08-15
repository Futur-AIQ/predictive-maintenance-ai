import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import type { EvaluationReport } from "@/types"

const metrics = [
  {
    key: "faithfulness" as const,
    label: "Faithfulness",
    description: "How factually accurate the AI responses are based on retrieved context",
  },
  {
    key: "answer_relevancy" as const,
    label: "Answer Relevancy",
    description: "How relevant the answers are to the questions asked",
  },
  {
    key: "context_precision" as const,
    label: "Context Precision",
    description: "Proportion of relevant context in retrieved documents",
  },
  {
    key: "context_recall" as const,
    label: "Context Recall",
    description: "How much relevant information was retrieved from the knowledge base",
  },
]

function scoreColor(score: number) {
  if (score >= 0.8) return "text-green-600"
  if (score >= 0.6) return "text-amber-600"
  return "text-red-600"
}

interface MetricsGridProps {
  report: EvaluationReport
}

export default function MetricsGrid({ report }: MetricsGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map(({ key, label, description }) => {
        const score = report[key]
        const pct = Math.round(score * 100)
        return (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className={cn("text-3xl font-bold", scoreColor(score))}>{pct}%</p>
              <Progress value={pct} className="h-2" />
              <p className="text-xs text-muted-foreground">{description}</p>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
