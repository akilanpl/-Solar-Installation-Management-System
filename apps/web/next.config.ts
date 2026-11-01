import type { NextConfig } from "next";
import { currentSourceBuildId } from "./src/lib/build-id";

const buildIdentity = currentSourceBuildId(process.cwd(), process.env);

const nextConfig: NextConfig = {
  env: { NEXT_PUBLIC_SOLAROPS_BUILD_ID: buildIdentity },
  poweredByHeader: false,
  generateBuildId: async () => currentSourceBuildId(process.cwd(), process.env),
  devIndicators: false,
  async headers() {
    return [{ source: "/:path*", headers: [{ key: "X-SolarOps-Frontend", value: buildIdentity }] }];
  },
  distDir: process.env.SOLAROPS_NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
