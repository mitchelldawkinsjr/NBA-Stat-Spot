"""
External API Rate Limiter Service
Tracks rate limits per API provider to prevent API bans.
Uses Redis or in-memory storage for rate limit tracking.
"""
from __future__ import annotations
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import os
import structlog

logger = structlog.get_logger()


class APIProvider(str, Enum):
    """Supported external API providers"""
    API_NBA = "api_nba"
    ESPN = "espn"


class RateLimitConfig:
    """Rate limit configuration for an API provider"""
    def __init__(
        self,
        requests_per_minute: int,
        requests_per_hour: Optional[int] = None,
        requests_per_day: Optional[int] = None
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day


class ExternalAPIRateLimiter:
    """
    Rate limiter for external API calls.
    Tracks requests per provider to prevent exceeding API limits.
    """
    
    def __init__(self):
        self._redis_client = None
        self._use_redis = False
        self._in_memory_storage: Dict[str, list] = {}  # provider -> list of timestamps
        
        # Initialize Redis if available
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
                self._use_redis = True
                logger.info("Using Redis for external API rate limiting")
            except Exception as e:
                logger.warning("Redis unavailable for rate limiting, using in-memory storage", error=str(e))
                self._use_redis = False
        
        # Load rate limit configurations from environment or use defaults
        # API-Sports.io free tier: 100 requests/day, 10 requests/minute
        # Paid tiers have higher limits (500+ requests/day)
        self._configs = {
            APIProvider.API_NBA: RateLimitConfig(
                requests_per_minute=int(os.getenv("API_NBA_RATE_LIMIT_PER_MINUTE", "10")),
                requests_per_day=int(os.getenv("API_NBA_RATE_LIMIT_PER_DAY", "100"))
            ),
            APIProvider.ESPN: RateLimitConfig(
                requests_per_minute=int(os.getenv("ESPN_RATE_LIMIT_PER_MINUTE", "100")),
                requests_per_hour=int(os.getenv("ESPN_RATE_LIMIT_PER_HOUR", "1000"))
            )
        }
    
    def can_make_request(self, provider: APIProvider) -> Tuple[bool, Optional[str]]:
        """
        Check if a request can be made without exceeding rate limits.
        
        Args:
            provider: API provider to check
            
        Returns:
            Tuple of (can_make_request, error_message)
            error_message is None if request can be made
        """
        config = self._configs.get(provider)
        if not config:
            return False, f"Unknown API provider: {provider}"
        
        now = datetime.utcnow()
        
        if self._use_redis and self._redis_client:
            return self._check_redis_limits(provider, config, now)
        else:
            return self._check_memory_limits(provider, config, now)
    
    def _check_redis_limits(
        self, 
        provider: APIProvider, 
        config: RateLimitConfig, 
        now: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check rate limits using Redis"""
        try:
            provider_key = f"rate_limit:{provider.value}"
            
            # Check per-minute limit
            minute_key = f"{provider_key}:minute:{now.strftime('%Y%m%d%H%M')}"
            minute_count = self._redis_client.get(minute_key)
            if minute_count and int(minute_count) >= config.requests_per_minute:
                return False, f"Rate limit exceeded: {config.requests_per_minute} requests/minute"
            
            # Check per-hour limit (if configured)
            if config.requests_per_hour:
                hour_key = f"{provider_key}:hour:{now.strftime('%Y%m%d%H')}"
                hour_count = self._redis_client.get(hour_key)
                if hour_count and int(hour_count) >= config.requests_per_hour:
                    return False, f"Rate limit exceeded: {config.requests_per_hour} requests/hour"
            
            # Check per-day limit (if configured)
            if config.requests_per_day:
                day_key = f"{provider_key}:day:{now.strftime('%Y%m%d')}"
                day_count = self._redis_client.get(day_key)
                if day_count and int(day_count) >= config.requests_per_day:
                    return False, f"Rate limit exceeded: {config.requests_per_day} requests/day"
            
            return True, None
            
        except Exception as e:
            logger.error("Error checking Redis rate limits", provider=provider.value, error=str(e))
            # Fall back to memory-based checking
            return self._check_memory_limits(provider, config, now)
    
    def _check_memory_limits(
        self, 
        provider: APIProvider, 
        config: RateLimitConfig, 
        now: datetime
    ) -> Tuple[bool, Optional[str]]:
        """Check rate limits using in-memory storage"""
        provider_key = provider.value
        
        if provider_key not in self._in_memory_storage:
            self._in_memory_storage[provider_key] = []
        
        timestamps = self._in_memory_storage[provider_key]
        
        # Clean up old timestamps (older than 24 hours)
        cutoff = now - timedelta(hours=24)
        timestamps[:] = [ts for ts in timestamps if ts > cutoff]
        
        # Check per-minute limit
        minute_cutoff = now - timedelta(minutes=1)
        minute_count = sum(1 for ts in timestamps if ts > minute_cutoff)
        if minute_count >= config.requests_per_minute:
            return False, f"Rate limit exceeded: {config.requests_per_minute} requests/minute"
        
        # Check per-hour limit (if configured)
        if config.requests_per_hour:
            hour_cutoff = now - timedelta(hours=1)
            hour_count = sum(1 for ts in timestamps if ts > hour_cutoff)
            if hour_count >= config.requests_per_hour:
                return False, f"Rate limit exceeded: {config.requests_per_hour} requests/hour"
        
        # Check per-day limit (if configured)
        if config.requests_per_day:
            day_cutoff = now - timedelta(days=1)
            day_count = sum(1 for ts in timestamps if ts > day_cutoff)
            if day_count >= config.requests_per_day:
                return False, f"Rate limit exceeded: {config.requests_per_day} requests/day"
        
        return True, None
    
    def record_request(self, provider: APIProvider) -> None:
        """
        Record that a request was made to an API provider.
        
        Args:
            provider: API provider that was called
        """
        now = datetime.utcnow()
        
        if self._use_redis and self._redis_client:
            self._record_redis_request(provider, now)
        else:
            self._record_memory_request(provider, now)
    
    def _record_redis_request(self, provider: APIProvider, now: datetime) -> None:
        """Record request in Redis"""
        try:
            provider_key = f"rate_limit:{provider.value}"
            
            # Increment per-minute counter
            minute_key = f"{provider_key}:minute:{now.strftime('%Y%m%d%H%M')}"
            self._redis_client.incr(minute_key)
            self._redis_client.expire(minute_key, 120)  # Expire after 2 minutes
            
            # Increment per-hour counter (if configured)
            config = self._configs.get(provider)
            if config and config.requests_per_hour:
                hour_key = f"{provider_key}:hour:{now.strftime('%Y%m%d%H')}"
                self._redis_client.incr(hour_key)
                self._redis_client.expire(hour_key, 7200)  # Expire after 2 hours
            
            # Increment per-day counter (if configured)
            if config and config.requests_per_day:
                day_key = f"{provider_key}:day:{now.strftime('%Y%m%d')}"
                self._redis_client.incr(day_key)
                self._redis_client.expire(day_key, 86400)  # Expire after 24 hours
                
        except Exception as e:
            logger.error("Error recording Redis request", provider=provider.value, error=str(e))
            # Fall back to memory
            self._record_memory_request(provider, now)
    
    def _record_memory_request(self, provider: APIProvider, now: datetime) -> None:
        """Record request in memory"""
        provider_key = provider.value
        
        if provider_key not in self._in_memory_storage:
            self._in_memory_storage[provider_key] = []
        
        self._in_memory_storage[provider_key].append(now)
    
    def get_rate_limit_status(self, provider: APIProvider) -> Dict[str, any]:
        """
        Get current rate limit status for a provider.
        
        Args:
            provider: API provider to check
            
        Returns:
            Dict with rate limit information
        """
        config = self._configs.get(provider)
        if not config:
            return {"error": f"Unknown API provider: {provider}"}
        
        now = datetime.utcnow()
        
        if self._use_redis and self._redis_client:
            return self._get_redis_status(provider, config, now)
        else:
            return self._get_memory_status(provider, config, now)
    
    def _get_redis_status(
        self, 
        provider: APIProvider, 
        config: RateLimitConfig, 
        now: datetime
    ) -> Dict[str, any]:
        """Get rate limit status from Redis"""
        try:
            provider_key = f"rate_limit:{provider.value}"
            
            status = {
                "provider": provider.value,
                "storage": "redis",
                "limits": {
                    "per_minute": config.requests_per_minute,
                    "per_hour": config.requests_per_hour,
                    "per_day": config.requests_per_day
                },
                "usage": {}
            }
            
            # Get per-minute usage
            minute_key = f"{provider_key}:minute:{now.strftime('%Y%m%d%H%M')}"
            minute_count = self._redis_client.get(minute_key)
            status["usage"]["per_minute"] = {
                "used": int(minute_count) if minute_count else 0,
                "limit": config.requests_per_minute,
                "remaining": config.requests_per_minute - (int(minute_count) if minute_count else 0)
            }
            
            # Get per-hour usage (if configured)
            if config.requests_per_hour:
                hour_key = f"{provider_key}:hour:{now.strftime('%Y%m%d%H')}"
                hour_count = self._redis_client.get(hour_key)
                status["usage"]["per_hour"] = {
                    "used": int(hour_count) if hour_count else 0,
                    "limit": config.requests_per_hour,
                    "remaining": config.requests_per_hour - (int(hour_count) if hour_count else 0)
                }
            
            # Get per-day usage (if configured)
            if config.requests_per_day:
                day_key = f"{provider_key}:day:{now.strftime('%Y%m%d')}"
                day_count = self._redis_client.get(day_key)
                status["usage"]["per_day"] = {
                    "used": int(day_count) if day_count else 0,
                    "limit": config.requests_per_day,
                    "remaining": config.requests_per_day - (int(day_count) if day_count else 0)
                }
            
            return status
            
        except Exception as e:
            logger.error("Error getting Redis rate limit status", provider=provider.value, error=str(e))
            return {"error": str(e)}
    
    def _get_memory_status(
        self, 
        provider: APIProvider, 
        config: RateLimitConfig, 
        now: datetime
    ) -> Dict[str, any]:
        """Get rate limit status from memory"""
        provider_key = provider.value
        
        if provider_key not in self._in_memory_storage:
            self._in_memory_storage[provider_key] = []
        
        timestamps = self._in_memory_storage[provider_key]
        
        # Clean up old timestamps
        cutoff = now - timedelta(hours=24)
        timestamps[:] = [ts for ts in timestamps if ts > cutoff]
        
        status = {
            "provider": provider.value,
            "storage": "memory",
            "limits": {
                "per_minute": config.requests_per_minute,
                "per_hour": config.requests_per_hour,
                "per_day": config.requests_per_day
            },
            "usage": {}
        }
        
        # Calculate per-minute usage
        minute_cutoff = now - timedelta(minutes=1)
        minute_count = sum(1 for ts in timestamps if ts > minute_cutoff)
        status["usage"]["per_minute"] = {
            "used": minute_count,
            "limit": config.requests_per_minute,
            "remaining": config.requests_per_minute - minute_count
        }
        
        # Calculate per-hour usage (if configured)
        if config.requests_per_hour:
            hour_cutoff = now - timedelta(hours=1)
            hour_count = sum(1 for ts in timestamps if ts > hour_cutoff)
            status["usage"]["per_hour"] = {
                "used": hour_count,
                "limit": config.requests_per_hour,
                "remaining": config.requests_per_hour - hour_count
            }
        
        # Calculate per-day usage (if configured)
        if config.requests_per_day:
            day_cutoff = now - timedelta(days=1)
            day_count = sum(1 for ts in timestamps if ts > day_cutoff)
            status["usage"]["per_day"] = {
                "used": day_count,
                "limit": config.requests_per_day,
                "remaining": config.requests_per_day - day_count
            }
        
        return status
    
    def get_all_providers_status(self) -> Dict[str, Dict[str, any]]:
        """Get rate limit status for all providers"""
        return {
            provider.value: self.get_rate_limit_status(provider)
            for provider in APIProvider
        }


# Global rate limiter instance
_rate_limiter: Optional[ExternalAPIRateLimiter] = None


def get_rate_limiter() -> ExternalAPIRateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = ExternalAPIRateLimiter()
    return _rate_limiter

