/**
 * API Configuration
 * Handles API base URL for different environments
 */

// Get API base URL from environment or use default
const getApiBaseUrl = (): string => {
  // In production, use Fly.io backend
  if (import.meta.env.PROD) {
    return 'https://nba-stat-spot-ai.fly.dev'
  }
  
  // In development, check for explicit API target
  // But ignore Docker hostnames (backend:8000) when running locally outside Docker
  const apiTarget = import.meta.env.VITE_API_TARGET
  if (apiTarget) {
    // If running in browser (not in Docker), Docker hostnames won't resolve
    // Check if it's a Docker hostname and we're likely running locally
    if (apiTarget.includes('://backend:') || apiTarget.includes('://backend/')) {
      // Docker hostname detected - only use it if we're actually in Docker
      // For local dev outside Docker, fall back to Vite proxy
      // (We can't reliably detect if we're in Docker from browser, so default to proxy)
      return ''
    }
    return apiTarget
  }
  
  // In development, use empty string to leverage Vite proxy to localhost:8000
  // This requires the local backend to be running on http://localhost:8000
  return ''
}

export const API_BASE_URL = getApiBaseUrl()

/**
 * Make an API request with the correct base URL
 */
export async function apiFetch(
  endpoint: string,
  options?: RequestInit
): Promise<Response> {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint
  
  // If API_BASE_URL is empty (dev mode with proxy), use relative path
  const url = API_BASE_URL 
    ? `${API_BASE_URL}/${cleanEndpoint}`
    : `/${cleanEndpoint}`
  
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
}

/**
 * Helper for GET requests
 */
export async function apiGet<T = any>(endpoint: string): Promise<T> {
  const res = await apiFetch(endpoint)
  if (!res.ok) {
    throw new Error(`API request failed: ${res.statusText}`)
  }
  return res.json()
}

/**
 * Helper for POST requests
 */
export async function apiPost<T = any>(
  endpoint: string,
  body?: any
): Promise<T> {
  const res = await apiFetch(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    throw new Error(`API request failed: ${res.statusText}`)
  }
  return res.json()
}

