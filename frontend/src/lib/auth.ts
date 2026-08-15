import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        username: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null

        try {
          // Step 1: Login to get tokens
          const loginRes = await fetch(`${API_URL}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              username: credentials.username as string,
              password: credentials.password as string,
            }),
          })

          if (!loginRes.ok) return null

          const tokenData = await loginRes.json()

          // Step 2: Fetch user info
          const meRes = await fetch(`${API_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${tokenData.access_token}` },
          })

          if (!meRes.ok) return null

          const userData = await meRes.json()

          return {
            id: String(userData.id),
            email: userData.email,
            name: userData.full_name,
            access_token: tokenData.access_token,
            refresh_token: tokenData.refresh_token,
            role: userData.role,
          }
        } catch {
          return null
        }
      },
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.accessToken = user.access_token
        token.refreshToken = user.refresh_token
        token.role = user.role
        token.userId = user.id
      }
      return token
    },
    session({ session, token }) {
      session.accessToken = token.accessToken as string
      session.user.role = token.role as string
      session.user.id = token.userId as string
      return session
    },
  },
  pages: {
    signIn: "/login",
  },
})

// Augment next-auth types
declare module "next-auth" {
  interface Session {
    accessToken: string
    user: {
      id: string
      email: string
      name: string
      role: string
    }
  }
  interface User {
    access_token: string
    refresh_token: string
    role: string
  }
}

