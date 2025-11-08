import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Vite proxy target for local development - proxies /api requests to local backend
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'
  
  // Check if we're building for GitHub Pages
  // If VITE_GITHUB_PAGES is set, use the repo name as base path
  const isGitHubPages = env.VITE_GITHUB_PAGES === 'true'
  const repoName = env.VITE_REPO_NAME || 'NBA-Stat-Spot'
  const base = isGitHubPages ? `/${repoName}/` : '/'
  
  return {
    plugins: [react()],
    base: base,
    server: {
      host: true,
      port: 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          // Proxies /api/* requests to local backend at localhost:8000 in dev mode
        },
      },
    },
    build: {
      outDir: 'dist',
      // Ensure environment variables are available at build time
      rollupOptions: {
        output: {
          // Preserve environment variables in production build
        }
      }
    }
  }
})
