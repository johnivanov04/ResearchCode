import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static HTML export: `next build` writes the whole site to `out/`, which Cloudflare Pages
  // serves (root directory `web`, output directory `out`). Export mode fails the build if a
  // page needs request-time rendering (cookies, headers, route handlers that read the request,
  // dynamic routes without generateStaticParams), so every page stays static.
  // Cache Components, Partial Prefetching, and `ensureStatic` cannot be used here: this version
  // of Next.js throws "PPR cannot be enabled in export mode" when `cacheComponents` is on.
  output: "export",
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
