import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync } from 'fs'
import { join } from 'path'

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
    plugins: [
      react(),
      // Plugin to copy index.html to 404.html for GitHub Pages SPA routing
      // This allows direct navigation to routes like /explore to work
      {
        name: 'copy-404-for-github-pages',
        closeBundle() {
          if (isGitHubPages) {
            const distPath = join(process.cwd(), 'frontend', 'dist')
            try {
              copyFileSync(
                join(distPath, 'index.html'),
                join(distPath, '404.html')
              )
              console.log('✅ Copied index.html to 404.html for GitHub Pages SPA routing')
            } catch (err) {
              console.warn('⚠️ Could not copy index.html to 404.html:', err)
            }
          }
        }
      }
    ],
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
