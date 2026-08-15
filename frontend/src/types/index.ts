// User types
export type UserRole = "admin" | "engineer"

export interface UserResponse {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  email: string
  password: string
  full_name: string
  role: UserRole
}

// Auth types
export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

// Equipment types
export type HealthStatus = "OK" | "WARNING" | "CRITICAL"
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

export interface EquipmentListItem {
  equipment_id: string
  equipment_type: string
  status: HealthStatus
  health_score: number
  rul: number
}

export interface SensorReadings {
  [key: string]: number | undefined
  T30?: number
  T50?: number
  Ps30?: number
  phi?: number
  BPR?: number
  W31?: number
  W32?: number
}

export interface HealthStatusResponse {
  equipment_id: string
  equipment_type: string
  status: HealthStatus
  health_score: number
  rul: number
  sensor_readings: SensorReadings
}

export interface MaintenanceHistoryItem {
  date: string
  event_type: string
  description: string
  technician?: string
}

// Diagnostic types
export interface DiagnosticRequest {
  equipment_id: string
  query: string
}

export interface DiagnosticResponse {
  session_id: string
  equipment_id: string
  diagnosis: string | null
  root_cause: string | null
  recommended_action: string | null
  confidence_score: number | null
  severity: Severity | null
  work_order_id: string | null
  work_order_created: boolean
  sources_used: string[] | null
  agent_steps: string[] | null
  created_at: string
}

// Work Order types — matches backend WorkOrderResponse schema exactly
export type WorkOrderStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED"

export interface WorkOrderResponse {
  id: number
  work_order_id: string
  equipment_id: string
  fault_code: string | null
  fault_description: string
  severity: Severity
  status: WorkOrderStatus
  recommended_action: string | null
  assigned_to: number | null
  created_by: number
  priority_score: number | null
  estimated_completion_hours: number | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface WorkOrderStatusUpdate {
  status: WorkOrderStatus
}

// Evaluation types — matches backend EvaluationReport schema exactly
export interface EvaluationReport {
  faithfulness: number
  answer_relevancy: number
  context_precision: number
  context_recall: number
  timestamp: string
  sample_count: number
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}
