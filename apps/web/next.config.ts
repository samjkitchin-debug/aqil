import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    AQIL_FOUNDER_INSIGHT_TOKEN: process.env.AQIL_FOUNDER_INSIGHT_TOKEN ?? "",
    AQIL_ALLOW_FOUNDER_INSIGHT_HEADER:
      process.env.AQIL_ALLOW_FOUNDER_INSIGHT_HEADER ?? "",
    AQIL_ALLOW_RESEARCH_FIXTURE: process.env.AQIL_ALLOW_RESEARCH_FIXTURE ?? "",
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [
      {
        source: "/my-wealth/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "private, no-store, max-age=0",
          },
        ],
      },
      {
        source: "/api/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "private, no-store, max-age=0",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
