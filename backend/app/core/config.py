from __future__ import annotations
from datetime import datetime
import os

# Season string helper: 'YYYY-YY'

def season_str(start_year: int) -> str:
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def current_candidate_season() -> str:
    """Return the likely current NBA season string based on today's date.
    Assumes season starts in Oct.
    """
    today = datetime.utcnow()
    year = today.year
    if today.month >= 10:
        return season_str(year)
    return season_str(year - 1)


def last_season_str() -> str:
    today = datetime.utcnow()
    year = today.year
    # Last completed season relative to Oct boundary
    if today.month >= 10:
        # If season likely started, last season starts in year-1
        return season_str(year - 1)
    # Before Oct, last season is year-1 to year
    return season_str(year - 1)


# CORS Configuration
def get_cors_origins() -> list[str]:
    """
    Get allowed CORS origins based on environment.
    Returns list of allowed origins.
    """
    # Check if we're in development mode
    is_fly_io = os.getenv("FLY_APP_NAME") is not None
    env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "")).lower()
    
    # If on Fly.io, always use production mode unless explicitly set to dev
    # Otherwise, default to development for local dev
    if is_fly_io:
        is_development = env_mode in ["development", "dev", "local"]
    else:
        # Local dev - default to development unless explicitly set to production
        is_development = env_mode not in ["production", "prod"]
    
    if is_development:
        # In development, allow all origins for easy local testing
        return ["*"]
    
    # In production, use configured origins from environment variable
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
        if origins:
            return origins
    
    # Fallback: if no CORS_ORIGINS is set in production, return empty list
    # This will require explicit configuration
    return []
