import axios from "axios"
import { getSession, signOut } from "next-auth/react"
import type {
  EquipmentListItem,
  HealthStatusResponse,
  DiagnosticRequest,
  DiagnosticResponse,
  WorkOrderResponse,
  WorkOrderStatusUpdate,
  EvaluationReport,
  UserResponse,
  UserCreate,
  SensorReadings,
  MaintenanceHistoryItem,
} from "@/types"

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
})

api.interceptors.request.use(async (config) => {
  const session = await getSession()
  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      await signOut({ callbackUrl: "/login" })
    }
    return Promise.reject(error)
  }
)

export const equipmentApi = {
  list: (): Promise<EquipmentListItem[]> =>
    api.get("/api/equipment/").then((r) => extractItems<EquipmentListItem>(r.data)),

  getHealth: (id: string): Promise<HealthStatusResponse> =>
    api.get(`/api/equipment/${id}/health`).then((r) => r.data),

  getSensors: (id: string): Promise<SensorReadings> =>
    api.get(`/api/equipment/${id}/sensors`).then((r) => {
      const d = r.data
      if (d?.sensors && typeof d.sensors === "object") {
        return {
          ...d.sensors,
          ...(d.current_cycle != null && { current_cycle: d.current_cycle }),
          ...(d.max_cycle     != null && { max_cycle:     d.max_cycle     }),
        }
      }
      return d
    }),

  getHistory: (id: string): Promise<MaintenanceHistoryItem[]> =>
    api.get(`/api/equipment/${id}/history`).then((r) => r.data),
}

export const diagnosticApi = {
  run: (data: DiagnosticRequest): Promise<DiagnosticResponse> =>
    api.post("/api/diagnostic/run", data).then((r) => r.data),

  history: (): Promise<DiagnosticResponse[]> =>
    api.get("/api/diagnostic/history").then((r) => extractItems<DiagnosticResponse>(r.data)),
}

// Helper: the backend may return a paginated envelope { items, total, ... } or a plain array
function extractItems<T>(data: T[] | { items: T[] }): T[] {
  if (Array.isArray(data)) return data
  if (data && typeof data === "object" && "items" in data) return data.items
  return []
}

export const workOrderApi = {
  list: (params?: {
    status?: string
    severity?: string
    page?: number
    size?: number
  }): Promise<WorkOrderResponse[]> =>
    api.get("/api/workorders/", { params }).then((r) => extractItems<WorkOrderResponse>(r.data)),

  updateStatus: (id: number, data: WorkOrderStatusUpdate): Promise<WorkOrderResponse> =>
    api.patch(`/api/workorders/${id}/status`, data).then((r) => r.data),

  delete: (id: number): Promise<void> =>
    api.delete(`/api/workorders/${id}`).then((r) => r.data),
}

export const evaluationApi = {
  run: (): Promise<EvaluationReport> =>
    api.get("/api/evaluation/run").then((r) => r.data),

  latest: (): Promise<EvaluationReport> =>
    api.get("/api/evaluation/latest").then((r) => r.data),
}

export const authApi = {
  me: (): Promise<UserResponse> =>
    api.get("/api/auth/me").then((r) => r.data),

  register: (data: UserCreate): Promise<UserResponse> =>
    api.post("/api/auth/register", data).then((r) => r.data),

  users: (): Promise<UserResponse[]> =>
    api.get("/api/auth/users").then((r) => extractItems<UserResponse>(r.data)),
}

export default api
