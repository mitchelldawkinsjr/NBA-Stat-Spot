# Cache System - Quick Start

## Switch Cache Provider

### Option 1: In Your Code (Anywhere)

```typescript
import { setCacheProvider } from '@/utils/cache'

// Switch to memory cache
setCacheProvider('memory')

// Switch back to localStorage
setCacheProvider('localStorage')
```

### Option 2: In App Initialization

```typescript
// In App.tsx or main.tsx
import './config/cache' // This will initialize with localStorage by default
```

### Option 3: Environment Variable

```bash
# In .env file
REACT_APP_CACHE_TYPE=memory
```

### Option 4: User Preference (localStorage)

```typescript
// User can set their preference
localStorage.setItem('cacheProvider', 'memory')

// Then reload - config/cache.ts will pick it up
```

## Current Default

- **Default Provider**: `localStorage`
- **Why**: Persists across page reloads, works offline
- **Switch To**: `memory` for testing or if localStorage has issues

## No Code Changes Needed

All existing code continues to work! The cache API is unchanged:

```typescript
import { getCache, setCache, clearCache } from '@/utils/cache'

// These work exactly the same regardless of provider
const data = getCache('my-resource')
setCache('my-resource', data)
clearCache('my-resource')
```

## Custom Provider Example

```typescript
import { setCacheProvider, type CacheProvider } from '@/utils/cache/types'

class IndexedDBCacheProvider implements CacheProvider {
  // Implement interface methods
  get<T>(resource: string, date?: string): T | null { /* ... */ }
  set<T>(resource: string, data: T, date?: string): void { /* ... */ }
  // ... other methods
}

setCacheProvider(new IndexedDBCacheProvider())
```

That's it! The cache system is now fully pluggable.

