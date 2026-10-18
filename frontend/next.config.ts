import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // NEXT_API_URL has no NEXT_PUBLIC_ prefix (Vercel's dashboard rejects that
  // prefix for this repo layout), so expose it to browser code explicitly.
  // Like NEXT_PUBLIC_ vars, it is inlined at build time.
  env: {
    NEXT_API_URL: process.env.NEXT_API_URL,
  },
};

export default nextConfig;
