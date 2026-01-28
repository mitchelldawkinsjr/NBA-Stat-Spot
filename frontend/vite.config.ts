import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { copyFileSync } from 'fs'
import { join } from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Vite proxy target for local development - proxies /api requests to local backend
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8001'
  
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
      // IMPORTANT: This must run AFTER Vite processes index.html and copies files from public/
      // The closeBundle hook ensures it runs at the very end of the build
      {
        name: 'copy-404-for-github-pages',
        closeBundle() {
          if (isGitHubPages) {
            // Use the build output directory from Vite config
            const distPath = join(process.cwd(), 'dist')
            try {
              const indexPath = join(distPath, 'index.html')
              const notFoundPath = join(distPath, '404.html')
              
              // Check if index.html exists
              if (!require('fs').existsSync(indexPath)) {
                console.warn('⚠️ index.html not found, cannot create 404.html')
                return
              }
              
              // Copy index.html to 404.html (this overwrites any 404.html from public/)
              copyFileSync(indexPath, notFoundPath)
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
          // Proxies /api/* requests to local backend at localhost:8001 in dev mode
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
