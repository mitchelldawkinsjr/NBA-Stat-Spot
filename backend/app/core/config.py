from __future__ import annotations
from datetime import datetime
import os

# Season string helper: canonical implementation in app.utils.season
from ..utils.season import get_current_season


def season_str(start_year: int) -> str:
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def current_candidate_season() -> str:
    """Return the likely current NBA season string based on today's date. Delegates to get_current_season()."""
    return get_current_season()


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
# Never use allow_origins=["*"] with allow_credentials=True (browser rejects it).
# So we always return an explicit list of origins.
_CORS_SAFE_ORIGINS = [
    "https://mitchelldawkinsjr.github.io",
    "https://nba-stat-spot.360web.cloud",
    "http://nba-stat-spot.360web.cloud",
    "https://nba.360web.cloud",
    "http://nba.360web.cloud",
]

_CORS_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
] + _CORS_SAFE_ORIGINS


def get_cors_origins() -> list[str]:
    """
    Get allowed CORS origins. Always returns an explicit list (never "*")
    so allow_credentials=True works in all environments.
    """
    env_mode = os.getenv("ENV", os.getenv("ENVIRONMENT", "")).lower()
    is_development = env_mode not in ["production", "prod"]

    if is_development:
        return list(dict.fromkeys(_CORS_DEV_ORIGINS))  # dedupe, keep order

    # Production: merge CORS_ORIGINS with safe list
    origins_set: set[str] = set(_CORS_SAFE_ORIGINS)
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        for origin in cors_origins_env.split(","):
            o = origin.strip()
            if o:
                origins_set.add(o)
    return list(origins_set)
