"use client"

import { Suspense } from "react"
import { useEffect, useState, useRef } from "react"
import { useSearchParams } from "next/navigation"
import { Loader2, Send } from "lucide-react"
import { diagnosticApi, equipmentApi } from "@/lib/api"
import { useDiagnosticStore } from "@/store/diagnosticStore"
import type { EquipmentListItem } from "@/types"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import ChatMessage from "@/components/diagnostic/ChatMessage"
import DiagnosticResult from "@/components/diagnostic/DiagnosticResult"
import AgentStepsTimeline from "@/components/diagnostic/AgentStepsTimeline"
import { toast } from "sonner"
import { format } from "date-fns"

const EXAMPLE_QUERIES = [
  "What is causing the high temperature readings?",
  "Analyze the current sensor anomalies",
  "What maintenance is required?",
  "Is this equipment safe to continue operating?",
]

function DiagnosticContent() {
  const searchParams = useSearchParams()
  const { sessions, currentSession, isRunning, addSession, setCurrentSession, setRunning } =
    useDiagnosticStore()

  const [equipment, setEquipment] = useState<EquipmentListItem[]>([])
  const [selectedEquipment, setSelectedEquipment] = useState(searchParams.get("equipment_id") || "")
  const [query, setQuery] = useState("")
  const [lastQuery, setLastQuery] = useState("") // tracks the query sent for display
  const [loadingEquipment, setLoadingEquipment] = useState(true)
  const resultRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    equipmentApi.list().then((list) => {
      setEquipment(list)
      setLoadingEquipment(false)
    })

    diagnosticApi.history().then((history) => {
      history.slice(0, 5).forEach((s) => addSession(s))
    }).catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = async () => {
    if (!selectedEquipment || !query.trim()) {
      toast.error("Please select equipment and enter a query")
      return
    }
    setLastQuery(query)
    setRunning(true)
    setCurrentSession(null)
    try {
      const result = await diagnosticApi.run({
        equipment_id: selectedEquipment,
        query: query,
      })
      addSession(result)
      setCurrentSession(result)
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth" }), 100)
    } catch {
      toast.error("Diagnostic failed. Please try again.")
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 h-full">
      {/* Left Panel */}
      <div className="lg:col-span-2 space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Run Diagnostic</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Equipment Select */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Equipment</label>
              {loadingEquipment ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Select value={selectedEquipment} onValueChange={setSelectedEquipment}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select equipment..." />
                  </SelectTrigger>
                  <SelectContent>
                    {equipment.map((eq) => (
                      <SelectItem key={eq.equipment_id} value={eq.equipment_id}>
                        {eq.equipment_id} — {eq.status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            {/* Query Input */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Query</label>
              <Textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Describe the issue or ask a question about the equipment..."
                rows={4}
                disabled={isRunning}
              />
              <div className="flex flex-wrap gap-1.5 mt-2">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuery(q)}
                    className="text-xs px-2 py-1 rounded-md bg-muted hover:bg-muted/80 text-muted-foreground"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            <Button
              onClick={handleRun}
              disabled={isRunning || !selectedEquipment || !query.trim()}
              className="w-full"
            >
              {isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Agent is analyzing...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Run Diagnostic
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Recent Sessions */}
        {sessions.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Recent Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {sessions.slice(0, 5).map((s) => (
                  <button
                    key={s.session_id}
                    onClick={() => setCurrentSession(s)}
                    className="w-full text-left p-2 rounded-md hover:bg-muted transition-colors"
                  >
                    <p className="text-xs font-medium">{s.equipment_id}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {s.diagnosis ?? "Diagnostic session"}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {format(new Date(s.created_at), "MMM d, HH:mm")}
                    </p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Right Panel */}
      <div className="lg:col-span-3 space-y-4" ref={resultRef}>
        {isRunning && (
          <Card>
            <CardContent className="py-12 text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="mt-3 text-sm text-muted-foreground">AI Agent is analyzing equipment data...</p>
              <p className="text-xs text-muted-foreground mt-1">Checking health, retrieving context, diagnosing...</p>
            </CardContent>
          </Card>
        )}

        {!isRunning && currentSession && (
          <>
            {/* Chat bubbles */}
            <Card>
              <CardContent className="pt-4 space-y-4">
                <ChatMessage role="user" content={lastQuery} />
                <ChatMessage
                  role="assistant"
                  content={`Based on my analysis of ${currentSession.equipment_id}: ${currentSession.diagnosis ?? "analysis complete."}`}
                />
              </CardContent>
            </Card>

            {/* Diagnostic result */}
            <DiagnosticResult result={currentSession} />

            {/* Agent steps */}
            {currentSession.agent_steps && currentSession.agent_steps.length > 0 && (
              <Card>
                <CardContent className="pt-4">
                  <AgentStepsTimeline steps={currentSession.agent_steps} />
                </CardContent>
              </Card>
            )}

            {/* Sources */}
            {currentSession.sources_used && currentSession.sources_used.length > 0 && (
              <Card>
                <CardContent className="pt-4">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                    Sources Used
                  </p>
                  <ul className="space-y-1">
                    {currentSession.sources_used.map((src, i) => (
                      <li key={i} className="text-xs text-muted-foreground">• {src}</li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {!isRunning && !currentSession && (
          <Card>
            <CardContent className="py-16 text-center">
              <p className="text-muted-foreground text-sm">
                Select equipment and enter a query to run an AI diagnostic
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default function DiagnosticPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-muted-foreground">Loading...</div>}>
      <DiagnosticContent />
    </Suspense>
  )
}
