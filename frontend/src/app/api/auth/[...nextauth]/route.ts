import { handlers } from "@/lib/auth"

// Login calls the backend, which can take a while to wake on a free-tier host
export const maxDuration = 60

export const { GET, POST } = handlers
