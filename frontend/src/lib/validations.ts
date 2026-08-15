import { z } from "zod"

export const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

export type LoginFormData = z.infer<typeof loginSchema>

export const userCreateSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(1, "Full name is required"),
  role: z.enum(["admin", "engineer"]),
})

export type UserCreateFormData = z.infer<typeof userCreateSchema>

export const workOrderStatusSchema = z.object({
  status: z.enum(["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]),
})

export type WorkOrderStatusFormData = z.infer<typeof workOrderStatusSchema>
