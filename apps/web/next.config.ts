import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  devIndicators: false,
  async headers() {
    return [{ source: "/:path*", headers: [{ key: "X-SolarOps-Frontend", value: "teammate-386f356-next-integration" }] }];
  },
  distDir: process.env.SOLAROPS_NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
