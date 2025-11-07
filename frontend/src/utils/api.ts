/**
 * API Configuration
 * Handles API base URL for different environments
 */

// Get API base URL from environment or use default
const getApiBaseUrl = (): string => {
  // In production (GitHub Pages), use environment variable or default backend URL
  if (import.meta.env.PROD) {
    return import.meta.env.VITE_API_TARGET || 'https://your-backend-url.com'
  }
  // In development, use proxy or localhost
  return import.meta.env.VITE_API_TARGET || ''
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

