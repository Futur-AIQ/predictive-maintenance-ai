import { create } from "zustand"
import type { DiagnosticResponse } from "@/types"

interface DiagnosticState {
  sessions: DiagnosticResponse[]
  currentSession: DiagnosticResponse | null
  isRunning: boolean
  addSession: (session: DiagnosticResponse) => void
  setCurrentSession: (session: DiagnosticResponse | null) => void
  setRunning: (running: boolean) => void
}

export const useDiagnosticStore = create<DiagnosticState>((set) => ({
  sessions: [],
  currentSession: null,
  isRunning: false,
  addSession: (session) =>
    set((state) => ({
      sessions: [
        session,
        ...state.sessions.filter((s) => s.session_id !== session.session_id),
      ].slice(0, 20),
    })),
  setCurrentSession: (currentSession) => set({ currentSession }),
  setRunning: (isRunning) => set({ isRunning }),
}))
