import type { NextConfig } from "next";

const backendUrl = (process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
