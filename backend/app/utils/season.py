"""
Season string utilities for NBA (e.g. "2025-26").
Season runs from October (year Y) through June (year Y+1).
"""
from datetime import datetime
from typing import Optional


def get_current_season() -> str:
    """
    Return the current NBA season string (e.g. "2025-26").
    From Oct 1 onward we use the new season; before that we use the previous year's season.
    """
    now = datetime.now()
    if now.month >= 10:
        start_year = now.year
    else:
        start_year = now.year - 1
    end_year_short = (start_year + 1) % 100
    return f"{start_year}-{end_year_short:02d}"


def get_previous_season(season: str) -> Optional[str]:
    """
    Return the season string for the year before (e.g. "2025-26" -> "2024-25").
    Returns None if season format is invalid or before 2000.
    """
    try:
        parts = season.split("-")
        if len(parts) != 2:
            return None
        start_year = int(parts[0])
        if start_year <= 2000:
            return None
        prev_start = start_year - 1
        prev_end_short = start_year % 100
        return f"{prev_start}-{prev_end_short:02d}"
    except (ValueError, AttributeError):
        return None
