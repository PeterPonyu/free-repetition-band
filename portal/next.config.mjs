import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  basePath: "/free-repetition-band",
  images: { unoptimized: true },
  trailingSlash: true,
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
