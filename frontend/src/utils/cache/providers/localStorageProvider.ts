/**
 * Local Storage Cache Provider
 * Implements cache using browser's localStorage
 */

import type { CacheProvider, CacheEntry } from '../types'

const CACHE_PREFIX = 'nba-stat-spot-cache'
const CACHE_VERSION = '1.0'

/**
 * Get today's date in YYYY-MM-DD format (local timezone)
 */
function getTodayDate(): string {
  return new Date().toLocaleDateString('en-CA')
}

/**
 * Get cache key for a specific resource and date
 */
function getCacheKey(resource: string, date?: string): string {
  const targetDate = date || getTodayDate()
  return `${CACHE_PREFIX}:${resource}:${targetDate}:${CACHE_VERSION}`
}

/**
 * Clean up old caches for a specific resource (keep only today and yesterday)
 */
function cleanupOldCaches(resource: string): void {
  try {
    const today = getTodayDate()
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toLocaleDateString('en-CA')
    
    const keys = Object.keys(localStorage)
    const prefix = `${CACHE_PREFIX}:${resource}:`
    
    keys.forEach(key => {
      if (key.startsWith(prefix)) {
        // Extract date from key (format: prefix:resource:date:version)
        const parts = key.split(':')
        if (parts.length >= 3) {
          const cacheDate = parts[parts.length - 2] // Date is second to last part
          if (cacheDate !== today && cacheDate !== yesterdayStr) {
            localStorage.removeItem(key)
          }
        }
      }
    })
  } catch (error) {
    console.error('Error cleaning up old caches:', error)
  }
}

/**
 * Clean up all old caches (all resources, keep only today and yesterday)
 */
function cleanupAllOldCaches(): void {
  try {
    const today = getTodayDate()
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toLocaleDateString('en-CA')
    
    const keys = Object.keys(localStorage)
    
    keys.forEach(key => {
      if (key.startsWith(CACHE_PREFIX)) {
        // Extract date from key (format: prefix:resource:date:version)
        const parts = key.split(':')
        if (parts.length >= 3) {
          const cacheDate = parts[parts.length - 2] // Date is second to last part
          if (cacheDate !== today && cacheDate !== yesterdayStr) {
            localStorage.removeItem(key)
          }
        }
      }
    })
  } catch (error) {
    console.error('Error cleaning up all old caches:', error)
  }
}

export class LocalStorageCacheProvider implements CacheProvider {
  get<T>(resource: string, date?: string): T | null {
    try {
      const targetDate = date || getTodayDate()
      const key = getCacheKey(resource, date)
      const cached = localStorage.getItem(key)
      
      if (!cached) {
        return null
      }
      
      const entry: CacheEntry<T> = JSON.parse(cached)
      
      // Check version
      if (entry.version !== CACHE_VERSION) {
        localStorage.removeItem(key)
        return null
      }
      
      // Check if cache is for requested date
      if (entry.date !== targetDate) {
        // Cache is for a different date, remove it
        localStorage.removeItem(key)
        return null
      }
      
      // Check if cache is too old (more than 24 hours)
      const now = Date.now()
      const maxAge = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
      if (now - entry.timestamp > maxAge) {
        localStorage.removeItem(key)
        return null
      }
      
      return entry.data
    } catch (error) {
      console.error('Error reading from cache:', error)
      return null
    }
  }

  set<T>(resource: string, data: T, date?: string): void {
    const targetDate = date || getTodayDate()
    try {
      const key = getCacheKey(resource, date)
      const entry: CacheEntry<T> = {
        data,
        date: targetDate,
        timestamp: Date.now(),
        version: CACHE_VERSION
      }
      
      localStorage.setItem(key, JSON.stringify(entry))
      
      // Clean up old caches for this resource (keep only today and yesterday)
      cleanupOldCaches(resource)
    } catch (error) {
      console.error('Error writing to cache:', error)
      // If storage is full, try to clear old caches
      if (error instanceof DOMException && error.code === 22) {
        cleanupAllOldCaches()
        try {
          const retryKey = getCacheKey(resource, date)
          const retryEntry: CacheEntry<T> = {
            data,
            date: targetDate,
            timestamp: Date.now(),
            version: CACHE_VERSION
          }
          localStorage.setItem(retryKey, JSON.stringify(retryEntry))
        } catch (retryError) {
          console.error('Failed to write to cache after cleanup:', retryError)
        }
      }
    }
  }

  clear(resource: string, date?: string): void {
    try {
      const key = getCacheKey(resource, date)
      localStorage.removeItem(key)
    } catch (error) {
      console.error('Error clearing cache:', error)
    }
  }

  clearAllForResource(resource: string): void {
    try {
      const keys = Object.keys(localStorage)
      const prefix = `${CACHE_PREFIX}:${resource}:`
      keys.forEach(key => {
        if (key.startsWith(prefix)) {
          localStorage.removeItem(key)
        }
      })
    } catch (error) {
      console.error('Error clearing all caches for resource:', error)
    }
  }

  clearAll(): void {
    try {
      const keys = Object.keys(localStorage)
      keys.forEach(key => {
        if (key.startsWith(CACHE_PREFIX)) {
          localStorage.removeItem(key)
        }
      })
    } catch (error) {
      console.error('Error clearing all caches:', error)
    }
  }

  getStats(): {
    totalEntries: number
    resources: Record<string, number>
    oldestEntry: number | null
    newestEntry: number | null
  } {
    const keys = Object.keys(localStorage).filter(key => key.startsWith(CACHE_PREFIX))
    const resources: Record<string, number> = {}
    let oldestEntry: number | null = null
    let newestEntry: number | null = null
    
    keys.forEach(key => {
      try {
        const cached = localStorage.getItem(key)
        if (cached) {
          const entry: CacheEntry<unknown> = JSON.parse(cached)
          
          // Count by resource
          const parts = key.split(':')
          if (parts.length >= 2) {
            const resource = parts[1]
            resources[resource] = (resources[resource] || 0) + 1
          }
          
          // Track timestamps
          if (oldestEntry === null || entry.timestamp < oldestEntry) {
            oldestEntry = entry.timestamp
          }
          if (newestEntry === null || entry.timestamp > newestEntry) {
            newestEntry = entry.timestamp
          }
        }
      } catch {
        // Skip invalid entries
      }
    })
    
    return {
      totalEntries: keys.length,
      resources,
      oldestEntry,
      newestEntry
    }
  }
}

