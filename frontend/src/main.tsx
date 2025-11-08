import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { SeasonProvider } from './context/SeasonContext'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      refetchOnMount: true,
      staleTime: 0, // Always consider data stale, but cache for quick navigation
      gcTime: 5 * 60 * 1000, // Keep unused data in cache for 5 minutes
      retry: 1, // Retry failed requests once
    },
  },
})

// Get base path for GitHub Pages if needed
const getBasePath = (): string => {
  // Check if we're on GitHub Pages (has repo name in path)
  if (import.meta.env.PROD && import.meta.env.VITE_GITHUB_PAGES === 'true') {
    const repoName = import.meta.env.VITE_REPO_NAME || 'NBA-Stat-Spot'
    return `/${repoName}`
  }
  return ''
}

const basePath = getBasePath()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={basePath}>
        <SeasonProvider>
        <App />
        </SeasonProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
