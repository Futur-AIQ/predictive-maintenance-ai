import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface WorkOrderFiltersProps {
  statusFilter: string
  severityFilter: string
  onStatusChange: (value: string) => void
  onSeverityChange: (value: string) => void
}

export default function WorkOrderFilters({
  statusFilter,
  severityFilter,
  onStatusChange,
  onSeverityChange,
}: WorkOrderFiltersProps) {
  return (
    <div className="flex flex-wrap gap-3">
      <Select value={statusFilter} onValueChange={onStatusChange}>
        <SelectTrigger className="w-40">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Statuses</SelectItem>
          <SelectItem value="OPEN">Open</SelectItem>
          <SelectItem value="IN_PROGRESS">In Progress</SelectItem>
          <SelectItem value="RESOLVED">Resolved</SelectItem>
          <SelectItem value="CLOSED">Closed</SelectItem>
        </SelectContent>
      </Select>

      <Select value={severityFilter} onValueChange={onSeverityChange}>
        <SelectTrigger className="w-40">
          <SelectValue placeholder="Severity" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All Severities</SelectItem>
          <SelectItem value="CRITICAL">Critical</SelectItem>
          <SelectItem value="HIGH">High</SelectItem>
          <SelectItem value="MEDIUM">Medium</SelectItem>
          <SelectItem value="LOW">Low</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
