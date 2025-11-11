"""
External API Client Service
Unified client for all external API calls with rate limiting, caching, retries, and error handling.
"""
from __future__ import annotations
from typing import Optional, Any, Dict
import httpx
import time
import structlog
from .external_api_rate_limiter import get_rate_limiter, APIProvider
from .cache_service import get_cache_service

logger = structlog.get_logger()


class ExternalAPIClient:
    """
    Unified client for external API calls.
    Handles rate limiting, caching, retries, and error handling.
    """
    
    def __init__(self):
        self.rate_limiter = get_rate_limiter()
        self.cache = get_cache_service()
        self._client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    def get_with_rate_limit(
        self,
        provider: APIProvider,
        endpoint: str,
        cache_key: Optional[str] = None,
        ttl: int = 300,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request with rate limiting and caching.
        
        Args:
            provider: API provider (API_NBA or ESPN)
            endpoint: Full URL endpoint
            cache_key: Optional cache key (if None, generated from endpoint)
            ttl: Cache TTL in seconds (default: 5 minutes)
            headers: Optional HTTP headers
            params: Optional query parameters
            use_cache: Whether to use cache (default: True)
            
        Returns:
            Response JSON as dict, or None on error
        """
        # Check cache first
        if use_cache:
            if cache_key is None:
                cache_key = f"external_api:{provider.value}:{endpoint}"
                if params:
                    import hashlib
                    params_str = str(sorted(params.items()))
                    params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                    cache_key = f"{cache_key}:{params_hash}"
            
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", provider=provider.value, endpoint=endpoint)
                return cached
        
        # Check rate limits
        can_request, error_msg = self.rate_limiter.can_make_request(provider)
        if not can_request:
            logger.warning("Rate limit exceeded", provider=provider.value, error=error_msg)
            # Return cached data if available (even if expired)
            if use_cache and cache_key:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    logger.info("Returning stale cache due to rate limit", provider=provider.value)
                    return cached
            return None
        
        # Make request with retries
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Record request before making it
                self.rate_limiter.record_request(provider)
                
                # Make the request
                response = self._client.get(
                    endpoint,
                    headers=headers,
                    params=params
                )
                
                # Handle rate limit responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(
                        "Rate limited by API",
                        provider=provider.value,
                        endpoint=endpoint,
                        retry_after=retry_after
                    )
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        # Return cached data if available
                        if use_cache and cache_key:
                            cached = self.cache.get(cache_key)
                            if cached is not None:
                                return cached
                        return None
                
                # Handle forbidden (API key issues)
                if response.status_code == 403:
                    logger.error(
                        "Forbidden - possible API key issue",
                        provider=provider.value,
                        endpoint=endpoint
                    )
                    return None
                
                # Handle other errors
                response.raise_for_status()
                
                # Parse JSON response
                data = response.json()
                
                # Cache successful response
                if use_cache and cache_key:
                    self.cache.set(cache_key, data, ttl=ttl)
                
                logger.info(
                    "External API request successful",
                    provider=provider.value,
                    endpoint=endpoint,
                    status_code=response.status_code
                )
                
                return data
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error in external API request",
                    provider=provider.value,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    attempt=attempt + 1
                )
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    # Return cached data if available
                    if use_cache and cache_key:
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            return cached
                    return None
                    
            except Exception as e:
                logger.error(
                    "Error in external API request",
                    provider=provider.value,
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    # Return cached data if available
                    if use_cache and cache_key:
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            return cached
                    return None
        
        return None
    
    def post_with_rate_limit(
        self,
        provider: APIProvider,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None,
        ttl: int = 300,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request with rate limiting and optional caching.
        
        Args:
            provider: API provider (API_NBA or ESPN)
            endpoint: Full URL endpoint
            data: POST data
            cache_key: Optional cache key
            ttl: Cache TTL in seconds (default: 5 minutes)
            headers: Optional HTTP headers
            use_cache: Whether to use cache (default: False for POST)
            
        Returns:
            Response JSON as dict, or None on error
        """
        # Check cache first (if enabled)
        if use_cache and cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", provider=provider.value, endpoint=endpoint)
                return cached
        
        # Check rate limits
        can_request, error_msg = self.rate_limiter.can_make_request(provider)
        if not can_request:
            logger.warning("Rate limit exceeded", provider=provider.value, error=error_msg)
            if use_cache and cache_key:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached
            return None
        
        # Make request with retries
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                # Record request
                self.rate_limiter.record_request(provider)
                
                # Make the request
                response = self._client.post(
                    endpoint,
                    json=data,
                    headers=headers
                )
                
                # Handle rate limit responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    logger.warning(
                        "Rate limited by API",
                        provider=provider.value,
                        endpoint=endpoint,
                        retry_after=retry_after
                    )
                    
                    if attempt < max_retries - 1:
                        time.sleep(retry_after)
                        continue
                    else:
                        if use_cache and cache_key:
                            cached = self.cache.get(cache_key)
                            if cached is not None:
                                return cached
                        return None
                
                # Handle forbidden
                if response.status_code == 403:
                    logger.error(
                        "Forbidden - possible API key issue",
                        provider=provider.value,
                        endpoint=endpoint
                    )
                    return None
                
                # Handle other errors
                response.raise_for_status()
                
                # Parse JSON response
                result = response.json()
                
                # Cache successful response (if enabled)
                if use_cache and cache_key:
                    self.cache.set(cache_key, result, ttl=ttl)
                
                logger.info(
                    "External API POST successful",
                    provider=provider.value,
                    endpoint=endpoint,
                    status_code=response.status_code
                )
                
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP error in external API POST",
                    provider=provider.value,
                    endpoint=endpoint,
                    status_code=e.response.status_code,
                    attempt=attempt + 1
                )
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    if use_cache and cache_key:
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            return cached
                    return None
                    
            except Exception as e:
                logger.error(
                    "Error in external API POST",
                    provider=provider.value,
                    endpoint=endpoint,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    if use_cache and cache_key:
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            return cached
                    return None
        
        return None
    
    def close(self):
        """Close the HTTP client"""
        if self._client:
            self._client.close()


# Global client instance
_client: Optional[ExternalAPIClient] = None


def get_external_api_client() -> ExternalAPIClient:
    """Get or create the global external API client instance"""
    global _client
    if _client is None:
        _client = ExternalAPIClient()
    return _client

