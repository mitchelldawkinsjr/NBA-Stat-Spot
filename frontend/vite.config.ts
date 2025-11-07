import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8000'
  
  return {
    plugins: [react()],
    // Base path for GitHub Pages (if using project pages)
    // Uncomment and set to your repo name if needed:
    // base: '/NBA-Stat-Spot/',
    server: {
      host: true,
      port: 5173,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
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
