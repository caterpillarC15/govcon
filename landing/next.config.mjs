import path from 'node:path'
import { fileURLToPath } from 'node:url'

const workspaceRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: workspaceRoot,
  reactStrictMode: true,
  // lucide-react@1.x ships ESM with `module` but no `exports` field; Next 15
  // webpack's module factory chokes on its subpath .mjs files
  // ("Cannot read properties of undefined (reading 'call')" in Icon.mjs).
  // Forcing transpilePackages routes it through Next's own SWC compiler,
  // bypassing the package's broken ESM resolution.
  transpilePackages: ['lucide-react'],
}

export default nextConfig
