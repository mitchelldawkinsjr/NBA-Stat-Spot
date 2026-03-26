/**
 * Client-side gate for /admin. When VITE_ADMIN_SECRET is set at build time,
 * the user must enter that same value once per browser session before seeing
 * the dashboard. Must match backend ADMIN_SECRET for API calls.
 */
export const ADMIN_PAGE_SESSION_KEY = 'nba_admin_unlocked'

export function isAdminGateEnabled(): boolean {
  return Boolean((import.meta.env.VITE_ADMIN_SECRET || '').trim())
}

/** True if gate is off, or user has unlocked this session. */
export function isAdminPageUnlocked(): boolean {
  if (!isAdminGateEnabled()) return true
  try {
    return sessionStorage.getItem(ADMIN_PAGE_SESSION_KEY) === '1'
  } catch {
    return false
  }
}

export function unlockAdminPage(password: string): boolean {
  const expected = (import.meta.env.VITE_ADMIN_SECRET || '').trim()
  if (!expected || password.trim() !== expected) return false
  try {
    sessionStorage.setItem(ADMIN_PAGE_SESSION_KEY, '1')
  } catch {
    /* ignore */
  }
  return true
}

export function lockAdminPage(): void {
  try {
    sessionStorage.removeItem(ADMIN_PAGE_SESSION_KEY)
  } catch {
    /* ignore */
  }
}
