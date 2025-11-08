# Cache System

A flexible, pluggable cache system for NBA Stat Spot with support for multiple storage backends.

## Features

- **Pluggable Providers**: Easily switch between localStorage, memory, or custom cache implementations
- **Date-based Caching**: Automatic date-based cache invalidation
- **Type-safe**: Full TypeScript support
- **Automatic Cleanup**: Removes old caches automatically
- **Storage Quota Handling**: Gracefully handles storage full errors

## Usage

### Basic Usage (Default: localStorage)

```typescript
import { getCache, setCache, clearCache } from '@/utils/cache'

// Get cached data
const data = getCache<MyDataType>('my-resource', '2025-01-15')

// Set cached data
setCache('my-resource', myData, '2025-01-15')

// Clear cache
clearCache('my-resource', '2025-01-15')
```

### Switching Cache Providers

#### Option 1: Use Built-in Providers

```typescript
import { setCacheProvider } from '@/utils/cache'

// Use localStorage (default)
setCacheProvider('localStorage')

// Use in-memory cache (useful for testing or SSR)
setCacheProvider('memory')
```

#### Option 2: Use a Custom Provider

```typescript
import { setCacheProvider, type CacheProvider } from '@/utils/cache'

class MyCustomCacheProvider implements CacheProvider {
  get<T>(resource: string, date?: string): T | null {
    // Your implementation
  }
  
  set<T>(resource: string, data: T, date?: string): void {
    // Your implementation
  }
  
  clear(resource: string, date?: string): void {
    // Your implementation
  }
  
  clearAllForResource(resource: string): void {
    // Your implementation
  }
  
  clearAll(): void {
    // Your implementation
  }
  
  getStats() {
    // Your implementation
  }
}

// Use your custom provider
setCacheProvider(new MyCustomCacheProvider())
```

### Configuration Example

Create a cache configuration file:

```typescript
// src/config/cache.ts
import { setCacheProvider } from '@/utils/cache'

// Set provider based on environment or user preference
const cacheType = process.env.REACT_APP_CACHE_TYPE || 'localStorage'
setCacheProvider(cacheType)

// Or based on feature flag
if (window.localStorage?.getItem('useMemoryCache') === 'true') {
  setCacheProvider('memory')
}
```

### Advanced Usage

```typescript
import { 
  getCacheProvider,
  getCacheStats,
  clearAllCaches,
  clearAllCachesForResource
} from '@/utils/cache'

// Get current provider
const provider = getCacheProvider()

// Get cache statistics
const stats = getCacheStats()
console.log(`Total entries: ${stats.totalEntries}`)
console.log(`Resources:`, stats.resources)

// Clear all caches for a specific resource
clearAllCachesForResource('daily-props-50')

// Clear all caches
clearAllCaches()
```

## Available Providers

### LocalStorageCacheProvider (Default)

- **Storage**: Browser's localStorage
- **Persistence**: Survives page reloads
- **Limitations**: ~5-10MB storage limit, synchronous API
- **Best for**: Production use, offline support

### MemoryCacheProvider

- **Storage**: In-memory Map
- **Persistence**: Lost on page reload
- **Limitations**: No persistence, limited by available memory
- **Best for**: Testing, SSR, temporary caching

## Creating Custom Providers

To create a custom provider, implement the `CacheProvider` interface:

```typescript
import type { CacheProvider } from '@/utils/cache/types'

export class MyCustomProvider implements CacheProvider {
  get<T>(resource: string, date?: string): T | null {
    // Implement get logic
  }
  
  set<T>(resource: string, data: T, date?: string): void {
    // Implement set logic
  }
  
  clear(resource: string, date?: string): void {
    // Implement clear logic
  }
  
  clearAllForResource(resource: string): void {
    // Implement clear all for resource
  }
  
  clearAll(): void {
    // Implement clear all
  }
  
  getStats() {
    // Return cache statistics
    return {
      totalEntries: 0,
      resources: {},
      oldestEntry: null,
      newestEntry: null
    }
  }
}
```

## Cache Entry Structure

All cache entries follow this structure:

```typescript
interface CacheEntry<T> {
  data: T                    // The cached data
  date: string              // YYYY-MM-DD format
  timestamp: number         // Unix timestamp
  version: string          // Cache version for migrations
}
```

## Date-based Invalidation

- Caches are automatically invalidated when the date changes
- Old caches (older than yesterday) are automatically cleaned up
- Caches older than 24 hours are considered stale

## Migration Guide

If you're using the old `cache.ts` file, your code will continue to work. However, for new code:

**Old way:**
```typescript
import { getCache, setCache } from '@/utils/cache'
```

**New way (same API, but now pluggable):**
```typescript
import { getCache, setCache, setCacheProvider } from '@/utils/cache'

// Optionally switch providers
setCacheProvider('memory')
```

The API remains the same, so no code changes are required unless you want to switch providers.

