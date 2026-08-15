import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

interface AgentStepsTimelineProps {
  steps: string[]
}

const stepEmoji = (step: string) => {
  if (step.toLowerCase().includes("health")) return "🔍"
  if (step.toLowerCase().includes("retriev") || step.toLowerCase().includes("context")) return "📚"
  if (step.toLowerCase().includes("diagnos")) return "🧠"
  if (step.toLowerCase().includes("work")) return "📋"
  if (step.toLowerCase().includes("respond") || step.toLowerCase().includes("answer")) return "✅"
  return "⚙️"
}

export default function AgentStepsTimeline({ steps }: AgentStepsTimelineProps) {
  if (!steps || steps.length === 0) return null

  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="steps">
        <AccordionTrigger className="text-sm">
          Agent Reasoning Steps ({steps.length})
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-3 pt-2">
            {steps.map((step, index) => (
              <div key={index} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary text-xs shrink-0">
                    {stepEmoji(step)}
                  </div>
                  {index < steps.length - 1 && (
                    <div className="w-px flex-1 bg-border mt-1" />
                  )}
                </div>
                <div className="pb-4 flex-1">
                  <p className="text-sm text-muted-foreground">{step}</p>
                </div>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}
