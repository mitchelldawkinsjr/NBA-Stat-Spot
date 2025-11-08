"""
Example: How to integrate CacheService with existing admin router caches

This shows how to migrate from module-level globals to persistent cache.
"""

from typing import Optional, Dict, Any
from datetime import date, datetime
from .cache_service import get_cache_service
from ..database import get_db
from sqlalchemy.orm import Session


def get_daily_props_cache(target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get daily props from cache.
    Replaces: _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    """
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        date_str = target_date or date.today().isoformat()
        cache_key = f"daily_props:{date_str}"
        return cache.get(cache_key, db=db)
    finally:
        db.close()


def set_daily_props_cache(data: Dict[str, Any], target_date: Optional[str] = None, ttl: int = 86400) -> bool:
    """
    Set daily props in cache.
    Replaces: _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    """
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        date_str = target_date or date.today().isoformat()
        cache_key = f"daily_props:{date_str}"
        return cache.set(cache_key, data, ttl=ttl, db=db)
    finally:
        db.close()


def is_daily_props_cache_valid(target_date: Optional[str] = None) -> bool:
    """
    Check if daily props cache is valid for the given date.
    """
    cached = get_daily_props_cache(target_date)
    return cached is not None


# Similar functions for high_hit_rate_cache and best_bets_cache...

def get_high_hit_rate_cache(target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get high hit rate cache"""
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        date_str = target_date or date.today().isoformat()
        cache_key = f"high_hit_rate:{date_str}"
        return cache.get(cache_key, db=db)
    finally:
        db.close()


def set_high_hit_rate_cache(data: Dict[str, Any], target_date: Optional[str] = None, ttl: int = 86400) -> bool:
    """Set high hit rate cache"""
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        date_str = target_date or date.today().isoformat()
        cache_key = f"high_hit_rate:{date_str}"
        return cache.set(cache_key, data, ttl=ttl, db=db)
    finally:
        db.close()


def get_best_bets_cache() -> Optional[list]:
    """Get best bets cache"""
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        cache_key = "best_bets:latest"
        return cache.get(cache_key, db=db)
    finally:
        db.close()


def set_best_bets_cache(data: list, ttl: int = 3600) -> bool:
    """Set best bets cache"""
    cache = get_cache_service()
    db = next(get_db())
    
    try:
        cache_key = "best_bets:latest"
        return cache.set(cache_key, data, ttl=ttl, db=db)
    finally:
        db.close()

