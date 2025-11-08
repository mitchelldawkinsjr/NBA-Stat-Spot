# Fly.io Cache Strategy

## Current State

### In-Memory Caches (cachetools TTLCache)
- **NBA API Service**: Teams, players, game logs (24hr TTL)
- **Stats Service**: Search results, logs (1hr TTL)
- **Admin Router**: Daily props, high hit rate, best bets (module-level globals)

### Problems on Fly.io
1. **No shared state**: Multiple instances don't share memory
2. **Ephemeral storage**: Caches lost on restart/deployment
3. **Cold starts**: Each instance rebuilds cache independently
4. **Inefficient**: Same data cached multiple times across instances

## Recommended Solution: Hybrid Cache Strategy

### Option 1: Redis (Best for Production) ⭐
**Pros:**
- Shared cache across all instances
- Fast, in-memory performance
- Built-in TTL support
- Fly.io has native Redis support
- Scales well

**Cons:**
- Additional service cost (~$3-5/month)
- Requires Redis client library

**Implementation:**
- Use Redis for shared caches (daily props, high hit rate, best bets)
- Keep in-memory cachetools for per-instance fast lookups
- Two-tier: Redis (shared) → Memory (local) → API call

### Option 2: SQLite with Persistent Volume (Cost-Effective)
**Pros:**
- No additional service cost
- Persistent across restarts
- Simple to implement
- Works with existing SQLite setup

**Cons:**
- File I/O slower than Redis
- Not ideal for high-frequency writes
- Single file can be a bottleneck

**Implementation:**
- Create cache table in SQLite
- Use Fly.io volumes for persistence
- Cache with TTL stored in database

### Option 3: Hybrid (Recommended for MVP)
**Pros:**
- Best of both worlds
- In-memory for speed, SQLite for persistence
- Graceful degradation
- Cost-effective

**Cons:**
- More complex implementation
- Need to sync between layers

**Implementation:**
1. **Layer 1**: In-memory (cachetools) - fastest, per-instance
2. **Layer 2**: SQLite cache table - persistent, shared file
3. **Layer 3**: API call - fetch fresh data

## Recommended Implementation Plan

### Phase 1: SQLite Cache Table (Immediate)
1. Create cache table in SQLite
2. Store daily props, high hit rate, best bets
3. Use Fly.io volume for persistence
4. Implement cache service with TTL

### Phase 2: Add Redis (Future Scaling)
1. Add Redis service to Fly.io
2. Use Redis for hot data (daily props)
3. Keep SQLite as backup/persistence layer
4. Implement two-tier cache

## Implementation Details

### SQLite Cache Schema
```sql
CREATE TABLE cache_entries (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,  -- JSON serialized
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expires_at ON cache_entries(expires_at);
```

### Cache Service Interface
```python
class CacheService:
    def get(key: str) -> Optional[Any]
    def set(key: str, value: Any, ttl: int)
    def delete(key: str)
    def clear_pattern(pattern: str)
    def cleanup_expired()
```

### Fly.io Volume Setup
```toml
[[mounts]]
  source = "nba_cache_data"
  destination = "/data"
```

## Migration Path

1. **Week 1**: Implement SQLite cache table + service
2. **Week 2**: Migrate admin router caches to SQLite
3. **Week 3**: Add Fly.io volume for persistence
4. **Week 4**: Monitor and optimize
5. **Future**: Add Redis if needed for scaling

## Cost Analysis

- **SQLite + Volume**: $0 additional (included in Fly.io)
- **Redis**: ~$3-5/month for small instance
- **Current**: $0 but inefficient (multiple cold starts)

## Performance Targets

- **Cache Hit Rate**: >80% for daily props
- **Cache Latency**: <10ms for in-memory, <50ms for SQLite
- **Cold Start Recovery**: <30 seconds to rebuild critical caches

