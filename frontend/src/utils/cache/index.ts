/**
 * Cache Manager
 * Centralized cache management with pluggable providers
 */

import type { CacheProvider } from './types'
import { LocalStorageCacheProvider } from './providers/localStorageProvider'
import { MemoryCacheProvider } from './providers/memoryProvider'

/**
 * Cache provider type
 */
export type CacheProviderType = 'localStorage' | 'memory'

/**
 * Get today's date in YYYY-MM-DD format (local timezone)
 */
export function getTodayDate(): string {
  return new Date().toLocaleDateString('en-CA')
}

/**
 * Check if a date string is today
 */
export function isToday(dateStr: string): boolean {
  return dateStr === getTodayDate()
}

// Default cache provider (can be changed via setCacheProvider)
let currentProvider: CacheProvider = new LocalStorageCacheProvider()

/**
 * Set the cache provider
 * @param provider - The cache provider instance or type
 */
export function setCacheProvider(provider: CacheProvider | CacheProviderType): void {
  if (typeof provider === 'string') {
    switch (provider) {
      case 'localStorage':
        currentProvider = new LocalStorageCacheProvider()
        break
      case 'memory':
        currentProvider = new MemoryCacheProvider()
        break
      default:
        throw new Error(`Unknown cache provider type: ${provider}`)
    }
  } else {
    currentProvider = provider
  }
}

/**
 * Get the current cache provider
 */
export function getCacheProvider(): CacheProvider {
  return currentProvider
}

/**
 * Get cached data for a resource and date
 */
export function getCache<T>(resource: string, date?: string): T | null {
  return currentProvider.get<T>(resource, date)
}

/**
 * Set cached data for a resource and date
 */
export function setCache<T>(resource: string, data: T, date?: string): void {
  currentProvider.set(resource, data, date)
}

/**
 * Clear cache for a specific resource and date
 */
export function clearCache(resource: string, date?: string): void {
  currentProvider.clear(resource, date)
}

/**
 * Clear all caches for a resource (all dates)
 */
export function clearAllCachesForResource(resource: string): void {
  currentProvider.clearAllForResource(resource)
}

/**
 * Clear all caches (all resources, all dates)
 */
export function clearAllCaches(): void {
  currentProvider.clearAll()
}

/**
 * Get cache statistics
 */
export function getCacheStats() {
  return currentProvider.getStats()
}

// Export provider classes for advanced usage
export { LocalStorageCacheProvider } from './providers/localStorageProvider'
export { MemoryCacheProvider } from './providers/memoryProvider'
export type { CacheProvider, CacheEntry } from './types'

