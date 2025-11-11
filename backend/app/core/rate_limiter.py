"""
Rate limiting middleware for FastAPI
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import os

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour", "100/minute"],  # Generous defaults
    storage_uri=os.getenv("REDIS_URL", "memory://")  # Use Redis if available, otherwise in-memory
)

# Custom rate limit exceeded handler
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "details": {
                "message": f"Too many requests. Limit: {exc.detail}",
                "retry_after": exc.retry_after
            },
            "path": request.url.path
        },
        headers={"Retry-After": str(exc.retry_after) if exc.retry_after else "60"}
    )

