/** @type {import('next').NextConfig} */

// For GitHub *project* Pages the site is served under /<repo>/. The Pages
// workflow sets PAGES_BASE_PATH=/<repo> so assets resolve; locally it's unset
// (served at root), and all data fetches in the app are relative so both work.
const basePath = process.env.PAGES_BASE_PATH || "";

const nextConfig = {
  output: "export", // static site -> dashboard/out/
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
};

export default nextConfig;
