import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components + Partial Prefetching are the defaults for new Next.js 16 apps.
  // Together with `ensureStatic = "navigation"` in the root layout, every page is
  // prerendered at build time and the build fails if anything becomes request-time.
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
