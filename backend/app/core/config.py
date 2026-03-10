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
# Origins that must be allowed in production so the app and API at 360web.cloud and GitHub Pages work
_CORS_SAFE_ORIGINS = [
    "https://mitchelldawkinsjr.github.io",
    "https://nba-stat-spot.360web.cloud",
    "http://nba-stat-spot.360web.cloud",
    "https://nba.360web.cloud",
    "http://nba.360web.cloud",
]


def get_cors_origins() -> list[str]:
    """
    Get allowed CORS origins based on environment.
    In production, always includes known app origins so /api/v1/props/daily etc. work from the frontend.
    """
    env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "")).lower()
    is_development = env_mode not in ["production", "prod"]

    if is_development:
        return ["*"]

    # Merge CORS_ORIGINS with safe list so 360web and GitHub Pages are always allowed
    origins_set: set[str] = set(_CORS_SAFE_ORIGINS)
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        for origin in cors_origins_env.split(","):
            o = origin.strip()
            if o:
                origins_set.add(o)
    return list(origins_set)
