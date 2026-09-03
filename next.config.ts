import type { NextConfig } from "next";

/**
 * BizPilot AI — Next.js configuration.
 *
 * Routing strategy:
 *  - On Vercel, Python serverless functions live in `/api/*.py` and are served
 *    natively by Vercel at `/api/...`. No rewrites are applied (`VERCEL=1`).
 *  - Locally, the Python API runs as a stdlib HTTP server (see scripts/dev_api.py)
 *    and Next.js proxies `/api/*` to it via rewrites below.
 */
const apiTarget = process.env.PYTHON_API_URL || "http://127.0.0.1:8787";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (process.env.VERCEL === "1") {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;