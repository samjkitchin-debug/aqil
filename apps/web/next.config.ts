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
    const privateRoutes = [
      "/",
      "/explore",
      "/explore/:path*",
      "/calendar",
      "/calendar/:path*",
      "/learn",
      "/learn/:path*",
      "/research",
      "/research/:path*",
      "/my-wealth",
      "/my-wealth/:path*",
      "/login",
      "/access-denied",
      "/auth/:path*",
    ];
    return [
      ...privateRoutes.map((source) => ({
        source,
        headers: [privateNoStore],
      })),
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
