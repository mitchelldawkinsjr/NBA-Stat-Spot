from __future__ import annotations
from datetime import datetime

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
