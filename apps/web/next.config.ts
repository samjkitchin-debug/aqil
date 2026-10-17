import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
    const privateNoStore = {
      key: "Cache-Control",
      value: "private, no-store, max-age=0",
    };
    const privateRoutes = ["/", "/explore", "/calendar", "/learn", "/research", "/my-wealth", "/api/:path*"];
    return privateRoutes.map((source) => ({
      source,
      headers: [privateNoStore],
    }));
  },
};

export default nextConfig;
