/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",            // static site -> dashboard/out/
  images: { unoptimized: true },
  trailingSlash: true,         // so relative fetch('results.json') resolves under any base path
};

export default nextConfig;
