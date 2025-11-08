/**
 * In-Memory Cache Provider
 * Implements cache using in-memory storage (useful for testing or SSR)
 */

import type { CacheProvider, CacheEntry } from '../types'

const CACHE_VERSION = '1.0'

/**
 * Get today's date in YYYY-MM-DD format (local timezone)
 */
function getTodayDate(): string {
  return new Date().toLocaleDateString('en-CA')
}

export class MemoryCacheProvider implements CacheProvider {
  private cache: Map<string, CacheEntry<unknown>> = new Map()

  private getCacheKey(resource: string, date?: string): string {
    const targetDate = date || getTodayDate()
    return `${resource}:${targetDate}:${CACHE_VERSION}`
  }

  get<T>(resource: string, date?: string): T | null {
    try {
      const targetDate = date || getTodayDate()
      const key = this.getCacheKey(resource, date)
      const entry = this.cache.get(key) as CacheEntry<T> | undefined
      
      if (!entry) {
        return null
      }
      
      // Check version
      if (entry.version !== CACHE_VERSION) {
        this.cache.delete(key)
        return null
      }
      
      // Check if cache is for requested date
      if (entry.date !== targetDate) {
        this.cache.delete(key)
        return null
      }
      
      // Check if cache is too old (more than 24 hours)
      const now = Date.now()
      const maxAge = 24 * 60 * 60 * 1000 // 24 hours in milliseconds
      if (now - entry.timestamp > maxAge) {
        this.cache.delete(key)
        return null
      }
      
      return entry.data as T
    } catch (error) {
      console.error('Error reading from cache:', error)
      return null
    }
  }

  set<T>(resource: string, data: T, date?: string): void {
    const targetDate = date || getTodayDate()
    try {
      const key = this.getCacheKey(resource, date)
      const entry: CacheEntry<T> = {
        data,
        date: targetDate,
        timestamp: Date.now(),
        version: CACHE_VERSION
      }
      
      this.cache.set(key, entry as CacheEntry<unknown>)
      
      // Clean up old entries (keep only today and yesterday)
      this.cleanupOldEntries()
    } catch (error) {
      console.error('Error writing to cache:', error)
    }
  }

  clear(resource: string, date?: string): void {
    try {
      const key = this.getCacheKey(resource, date)
      this.cache.delete(key)
    } catch (error) {
      console.error('Error clearing cache:', error)
    }
  }

  clearAllForResource(resource: string): void {
    const keysToDelete: string[] = []
    this.cache.forEach((_, key) => {
      if (key.startsWith(`${resource}:`)) {
        keysToDelete.push(key)
      }
    })
    keysToDelete.forEach(key => this.cache.delete(key))
  }

  clearAll(): void {
    this.cache.clear()
  }

  getStats(): {
    totalEntries: number
    resources: Record<string, number>
    oldestEntry: number | null
    newestEntry: number | null
  } {
    const resources: Record<string, number> = {}
    let oldestEntry: number | null = null
    let newestEntry: number | null = null
    
    this.cache.forEach((entry, key) => {
      try {
        // Count by resource
        const parts = key.split(':')
        if (parts.length >= 1) {
          const resource = parts[0]
          resources[resource] = (resources[resource] || 0) + 1
        }
        
        // Track timestamps
        if (oldestEntry === null || entry.timestamp < oldestEntry) {
          oldestEntry = entry.timestamp
        }
        if (newestEntry === null || entry.timestamp > newestEntry) {
          newestEntry = entry.timestamp
        }
      } catch {
        // Skip invalid entries
      }
    })
    
    return {
      totalEntries: this.cache.size,
      resources,
      oldestEntry,
      newestEntry
    }
  }

  private cleanupOldEntries(): void {
    const today = getTodayDate()
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toLocaleDateString('en-CA')
    
    const keysToDelete: string[] = []
    
    this.cache.forEach((entry, key) => {
      if (entry.date !== today && entry.date !== yesterdayStr) {
        keysToDelete.push(key)
      }
    })
    
    keysToDelete.forEach(key => this.cache.delete(key))
  }
}

