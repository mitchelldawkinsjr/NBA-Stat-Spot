"""
Cache Service for Fly.io
Supports both SQLite (persistent) and Redis (shared) backends.
Falls back gracefully if Redis is unavailable.
"""
from __future__ import annotations
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import json
import os
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.sql import func
from ..database import Base, get_db


class CacheEntry(Base):
    """SQLite cache table for persistent caching"""
    __tablename__ = "cache_entries"
    
    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)  # JSON serialized
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),
    )


class CacheService:
    """
    Unified cache service with SQLite persistence and optional Redis support.
    
    Usage:
        cache = CacheService()
        cache.set("daily_props_2025-01-15", data, ttl=86400)
        data = cache.get("daily_props_2025-01-15")
    """
    
    def __init__(self, use_redis: Optional[bool] = None):
        """
        Initialize cache service.
        
        Args:
            use_redis: If True, use Redis. If False, use SQLite only.
                      If None, auto-detect based on REDIS_URL env var.
        """
        self._redis_client = None
        self._use_redis = False
        
        # Auto-detect Redis availability
        if use_redis is None:
            redis_url = os.getenv("REDIS_URL")
            self._use_redis = redis_url is not None and redis_url != ""
        else:
            self._use_redis = use_redis
        
        # Initialize Redis if available
        if self._use_redis:
            try:
                import redis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self._redis_client.ping()
            except Exception as e:
                # Redis unavailable, fall back to SQLite
                import structlog
                logger = structlog.get_logger()
                logger.warning("Redis unavailable, falling back to SQLite cache", error=str(e))
                self._use_redis = False
                self._redis_client = None
    
    def get(self, key: str, db: Optional[Session] = None) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            db: Optional database session (for SQLite)
        
        Returns:
            Cached value or None if not found/expired
        """
        # Try Redis first if available
        if self._use_redis and self._redis_client:
            try:
                value = self._redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception:
                # Redis error, fall back to SQLite
                pass
        
        # Fall back to SQLite
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            entry = db.query(CacheEntry).filter(CacheEntry.key == key).first()
            if entry:
                # Check if expired
                if entry.expires_at < datetime.utcnow():
                    db.delete(entry)
                    db.commit()
                    return None
                return json.loads(entry.value)
            return None
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error reading from SQLite cache", error=str(e))
            return None
        finally:
            if should_close:
                db.close()
    
    def set(self, key: str, value: Any, ttl: int = 3600, db: Optional[Session] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 1 hour)
            db: Optional database session (for SQLite)
        
        Returns:
            True if successful, False otherwise
        """
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        value_json = json.dumps(value)
        
        # Set in Redis if available
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.setex(key, ttl, value_json)
            except Exception:
                # Redis error, continue to SQLite
                pass
        
        # Also set in SQLite for persistence
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            entry = db.query(CacheEntry).filter(CacheEntry.key == key).first()
            if entry:
                entry.value = value_json
                entry.expires_at = expires_at
                entry.updated_at = datetime.utcnow()
            else:
                entry = CacheEntry(
                    key=key,
                    value=value_json,
                    expires_at=expires_at
                )
                db.add(entry)
            db.commit()
            return True
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error writing to SQLite cache", error=str(e))
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def delete(self, key: str, db: Optional[Session] = None) -> bool:
        """Delete a cache entry"""
        # Delete from Redis
        if self._use_redis and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception:
                pass
        
        # Delete from SQLite
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            entry = db.query(CacheEntry).filter(CacheEntry.key == key).first()
            if entry:
                db.delete(entry)
                db.commit()
            return True
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error deleting from SQLite cache", error=str(e))
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def clear_pattern(self, pattern: str, db: Optional[Session] = None) -> int:
        """
        Clear all cache entries matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "daily_props_*")
            db: Optional database session
        
        Returns:
            Number of entries deleted
        """
        count = 0
        
        # Clear from Redis (supports wildcards)
        if self._use_redis and self._redis_client:
            try:
                keys = self._redis_client.keys(pattern.replace("*", "*"))
                if keys:
                    self._redis_client.delete(*keys)
                    count += len(keys)
            except Exception:
                pass
        
        # Clear from SQLite (simple LIKE pattern)
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            sql_pattern = pattern.replace("*", "%")
            entries = db.query(CacheEntry).filter(CacheEntry.key.like(sql_pattern)).all()
            count += len(entries)
            for entry in entries:
                db.delete(entry)
            db.commit()
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error clearing pattern from SQLite cache", error=str(e))
            db.rollback()
        finally:
            if should_close:
                db.close()
        
        return count
    
    def cleanup_expired(self, db: Optional[Session] = None) -> int:
        """
        Remove all expired cache entries.
        
        Returns:
            Number of entries deleted
        """
        count = 0
        
        # Redis handles TTL automatically, but we can clean up manually
        # (Redis auto-expires, so this is mainly for SQLite)
        
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            now = datetime.utcnow()
            entries = db.query(CacheEntry).filter(CacheEntry.expires_at < now).all()
            count = len(entries)
            for entry in entries:
                db.delete(entry)
            db.commit()
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error cleaning up expired cache entries", error=str(e))
            db.rollback()
        finally:
            if should_close:
                db.close()
        
        return count
    
    def get_stats(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = {
            "backend": "redis" if self._use_redis else "sqlite",
            "redis_available": self._use_redis and self._redis_client is not None,
            "total_entries": 0,
            "expired_entries": 0,
        }
        
        if db is None:
            from ..database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            now = datetime.utcnow()
            stats["total_entries"] = db.query(CacheEntry).count()
            stats["expired_entries"] = db.query(CacheEntry).filter(CacheEntry.expires_at < now).count()
            
            if self._use_redis and self._redis_client:
                try:
                    stats["redis_keys"] = self._redis_client.dbsize()
                except Exception:
                    pass
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error getting cache stats", error=str(e))
        finally:
            if should_close:
                db.close()
        
        return stats


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service instance"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

