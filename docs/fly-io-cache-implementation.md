# Fly.io Cache Implementation Guide

## Quick Start

### 1. Database Migration

The cache table will be created automatically when you start the app (via SQLAlchemy Base.metadata.create_all).

To manually create:
```python
from backend.app.database import Base, engine
from backend.app.services.cache_service import CacheEntry
Base.metadata.create_all(bind=engine)
```

### 2. Basic Usage

```python
from backend.app.services.cache_service import get_cache_service

cache = get_cache_service()

# Set cache
cache.set("daily_props:2025-01-15", data, ttl=86400)  # 24 hours

# Get cache
data = cache.get("daily_props:2025-01-15")

# Delete cache
cache.delete("daily_props:2025-01-15")

# Clear pattern
cache.clear_pattern("daily_props:*")
```

### 3. Integration with Admin Router

Replace module-level globals:

**Before:**
```python
_daily_props_cache: Optional[Dict] = None
_daily_props_cache_date: Optional[date] = None
```

**After:**
```python
from ..services.cache_service import get_cache_service

def get_daily_props(target_date: str):
    cache = get_cache_service()
    return cache.get(f"daily_props:{target_date}")
```

### 4. Fly.io Volume Setup (Optional but Recommended)

Add to `fly.toml`:
```toml
[[mounts]]
  source = "nba_cache_data"
  destination = "/data"
```

Update DATABASE_URL:
```toml
[env]
  DATABASE_URL = "sqlite:////data/nba_props.db"
```

Create volume:
```bash
fly volumes create nba_cache_data --size 1 --region iad
```

### 5. Redis Setup (Optional, for Scaling)

Create Redis instance:
```bash
fly redis create
```

Set REDIS_URL:
```bash
fly secrets set REDIS_URL="redis://your-redis-url"
```

The cache service will automatically detect and use Redis if REDIS_URL is set.

## Migration Checklist

- [ ] Cache table created in database
- [ ] CacheService integrated with admin router
- [ ] Module-level globals replaced with cache service calls
- [ ] Fly.io volume created (optional)
- [ ] Redis configured (optional, for scaling)
- [ ] Cache cleanup job scheduled (optional)
- [ ] Monitoring/logging added

## Performance Tips

1. **Use appropriate TTLs**:
   - Daily props: 86400 (24 hours)
   - High hit rate: 86400 (24 hours)
   - Best bets: 3600 (1 hour)
   - Player stats: 3600 (1 hour)

2. **Cache key patterns**:
   - Use consistent prefixes: `daily_props:`, `high_hit_rate:`, `best_bets:`
   - Include date in key: `daily_props:2025-01-15`

3. **Cleanup expired entries**:
   - Run cleanup job daily: `cache.cleanup_expired()`

4. **Monitor cache stats**:
   - Use `cache.get_stats()` for monitoring
   - Track hit rates and cache sizes

## Troubleshooting

### Cache not persisting
- Check Fly.io volume is mounted correctly
- Verify DATABASE_URL points to persistent location
- Check file permissions

### Redis not working
- Verify REDIS_URL is set correctly
- Check Redis instance is running
- Service will fall back to SQLite automatically

### Cache table missing
- Ensure CacheEntry is imported in main.py
- Run Base.metadata.create_all() manually if needed

