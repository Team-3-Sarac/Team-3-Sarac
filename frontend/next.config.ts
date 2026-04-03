import type { NextConfig } from "next";
import { join } from "path";

const nextConfig: NextConfig = {
  experimental: {
    turbopack: {
      root: join(process.cwd())
    }
  }
};

export default nextConfig;
