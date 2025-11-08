/**
 * Cache Provider Interface
 * Defines the contract for cache implementations
 */

export interface CacheEntry<T> {
  data: T
  date: string // YYYY-MM-DD
  timestamp: number // Unix timestamp
  version: string
}

export interface CacheProvider {
  /**
   * Get cached data for a resource and date
   */
  get<T>(resource: string, date?: string): T | null

  /**
   * Set cached data for a resource and date
   */
  set<T>(resource: string, data: T, date?: string): void

  /**
   * Clear cache for a specific resource and date
   */
  clear(resource: string, date?: string): void

  /**
   * Clear all caches for a resource (all dates)
   */
  clearAllForResource(resource: string): void

  /**
   * Clear all caches (all resources, all dates)
   */
  clearAll(): void

  /**
   * Get cache statistics
   */
  getStats(): {
    totalEntries: number
    resources: Record<string, number>
    oldestEntry: number | null
    newestEntry: number | null
  }
}

