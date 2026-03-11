/**
 * API Configuration
 * Handles API base URL for different environments
 */

// Get API base URL from environment or use default
const getApiBaseUrl = (): string => {
  // Same-origin: when app is loaded from nba.360web.cloud, use relative /api/* (no cross-origin).
  if (typeof window !== 'undefined' && window.location.hostname === 'nba.360web.cloud') {
    return ''
  }
  // When frontend is hosted on same domain as API (e.g. VPS behind NPM), use relative paths
  // so /api/* is proxied by nginx to the backend. No CORS, same origin.
  if (import.meta.env.VITE_USE_RELATIVE_API === 'true') {
    return ''
  }

  // Check for explicit API target (set via VITE_API_TARGET env var)
  // This allows overriding the backend URL via GitHub Secrets or build-time env vars
  const apiTarget = import.meta.env.VITE_API_TARGET
  if (apiTarget) {
    // If running in browser (not in Docker), Docker hostnames won't resolve
    // Check if it's a Docker hostname and we're likely running locally
    if (apiTarget.includes('://backend:') || apiTarget.includes('://backend/')) {
      // Docker hostname detected - only use it if we're actually in Docker
      // For local dev outside Docker, fall back to Vite proxy
      // (We can't reliably detect if we're in Docker from browser, so default to proxy)
      if (!import.meta.env.PROD) {
        return ''
      }
    }
    return apiTarget
  }
  
  // In production (e.g. GitHub Pages), use mitch-cloud backend as default
  if (import.meta.env.PROD) {
    return 'https://nba-stat-spot.360web.cloud'
  }
  
  // In development, use empty string to leverage Vite proxy (default localhost:8007)
  return ''
}

export const API_BASE_URL = getApiBaseUrl()

/** Human-readable API base for debugging (e.g. in Admin). */
export function getApiBaseDisplay(): string {
  if (API_BASE_URL) return API_BASE_URL
  if (typeof window !== 'undefined') return `${window.location.origin} (proxied or same-origin)`
  return '(same-origin)'
}

const FALLBACK_API_BASE = 'https://nba-stat-spot.360web.cloud'

/**
 * Make an API request with the correct base URL.
 * If same-origin request fails (e.g. /api not proxied), retries with backend URL once.
 */
export async function apiFetch(
  endpoint: string,
  options?: RequestInit
): Promise<Response> {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint

  const url = API_BASE_URL
    ? `${API_BASE_URL}/${cleanEndpoint}`
    : `/${cleanEndpoint}`

  const doFetch = (targetUrl: string) =>
    fetch(targetUrl, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

  try {
    let res = await doFetch(url)
    // If same-origin failed (404 = /api not proxied, 502/503), retry with backend URL when on app domain
    if (
      !res.ok &&
      typeof window !== 'undefined' &&
      window.location.hostname === 'nba.360web.cloud' &&
      url.startsWith('/')
    ) {
      const fallbackUrl = `${FALLBACK_API_BASE}/${cleanEndpoint}`
      res = await doFetch(fallbackUrl)
    }
    return res
  } catch (err) {
    // Network/CORS error on same-origin; retry with backend URL when on app domain
    if (
      typeof window !== 'undefined' &&
      window.location.hostname === 'nba.360web.cloud' &&
      url.startsWith('/')
    ) {
      const fallbackUrl = `${FALLBACK_API_BASE}/${cleanEndpoint}`
      return doFetch(fallbackUrl)
    }
    throw err
  }
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
    // Create error with status code for better handling
    const error: any = new Error(`API request failed: ${res.statusText}`)
    error.response = { status: res.status, statusText: res.statusText }
    error.message = error.message.includes('429') ? '429' : error.message
    throw error
  }
  return res.json()
}

