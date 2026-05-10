import path from 'node:path'
import { fileURLToPath } from 'node:url'

const workspaceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: workspaceRoot,
  reactStrictMode: true,
  // lucide-react@1.x ESM-resolution fix — see landing/next.config.mjs.
  transpilePackages: ['lucide-react'],
}

export default nextConfig
