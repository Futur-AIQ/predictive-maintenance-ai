import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // NEXT_API_URL has no NEXT_PUBLIC_ prefix (Vercel's dashboard rejects that
  // prefix for this repo layout), so expose it to browser code explicitly.
  // Like NEXT_PUBLIC_ vars, it is inlined at build time. A trailing slash is
  // dropped so paths don't become "//api/...".
  env: {
    NEXT_API_URL: process.env.NEXT_API_URL?.trim().replace(/\/+$/, ""),
  },
};

export default nextConfig;
