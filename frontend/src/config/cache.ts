/**
 * Cache Configuration
 * 
 * Configure the cache provider here.
 * You can switch between 'localStorage' and 'memory', or use a custom provider.
 * 
 * To switch providers, simply change the provider type below or use environment variables.
 */

import { setCacheProvider, type CacheProviderType } from '../utils/cache'

// Get cache type from environment variable or use default
// In Vite, use import.meta.env instead of process.env
const cacheType: CacheProviderType = 
  (import.meta.env.VITE_CACHE_TYPE as CacheProviderType) || 
  'localStorage'

// Initialize the cache provider
setCacheProvider(cacheType)

// Optional: You can also check localStorage for user preference
if (typeof window !== 'undefined' && window.localStorage) {
  const userPreference = window.localStorage.getItem('cacheProvider')
  if (userPreference === 'memory' || userPreference === 'localStorage') {
    setCacheProvider(userPreference as CacheProviderType)
  }
}

// Export for advanced usage
export { cacheType }

