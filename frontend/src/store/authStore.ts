import { create } from "zustand"
import type { UserResponse } from "@/types"

interface AuthState {
  user: UserResponse | null
  isLoading: boolean
  setUser: (user: UserResponse | null) => void
  clearUser: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  setUser: (user) => set({ user }),
  clearUser: () => set({ user: null }),
  setLoading: (isLoading) => set({ isLoading }),
}))
