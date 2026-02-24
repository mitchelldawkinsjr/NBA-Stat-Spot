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

# Custom rate limit exceeded handler (adds CORS so browser gets valid response)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors"""
    from fastapi.responses import JSONResponse
    from .config import get_cors_origins

    retry_after = getattr(exc, "retry_after", None) or 60
    response = JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "details": {
                "message": f"Too many requests. Limit: {exc.detail}",
                "retry_after": retry_after,
            },
            "path": request.url.path,
        },
        headers={"Retry-After": str(retry_after)},
    )
    # CORS: echo Origin when allowed (required when credentials=true)
    origins = get_cors_origins()
    origin = request.headers.get("origin")
    allow_origin = None
    if origins == ["*"] and origin:
        allow_origin = origin
    elif origin and origin in origins:
        allow_origin = origin
    if allow_origin:
        response.headers["Access-Control-Allow-Origin"] = allow_origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

