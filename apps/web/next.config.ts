import type { NextConfig } from "next";
import { currentSourceBuildId } from "./src/lib/build-id";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  generateBuildId: async () => currentSourceBuildId(process.cwd(), process.env),
  devIndicators: false,
  async headers() {
    return [{ source: "/:path*", headers: [{ key: "X-SolarOps-Frontend", value: "teammate-72db4a1-phase3-candidate" }] }];
  },
  distDir: process.env.SOLAROPS_NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
