"""Read-only odds endpoints (lines synced from The Odds API)."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.rate_limiter import limiter
from ..database import get_db
from ..services.odds_service import get_game_totals_for_date, get_player_odds_comparison

router = APIRouter(prefix="/api/v1/odds", tags=["odds_v1"])


@router.get("/player/{player_id}")
@limiter.limit("60/minute")
def get_player_live_odds(
    request: Request,
    player_id: int,
    game_date: Optional[str] = Query(None, description="Game date YYYY-MM-DD (optional)"),
    db: Session = Depends(get_db),
):
    """Per-book prop lines for a player (PTS/REB/AST/3PM) from synced Odds API data."""
    return get_player_odds_comparison(db, player_id, game_date)


@router.get("/nba/game-totals")
@limiter.limit("60/minute")
def get_nba_game_totals(
    request: Request,
    date: Optional[str] = Query(None, description="Slate date YYYY-MM-DD; omit for all cached totals"),
    db: Session = Depends(get_db),
):
    """Game total (over/under) lines by book, keyed by Odds API event id."""
    gd = None
    if date:
        try:
            gd = datetime.strptime(date[:10], "%Y-%m-%d").date()
        except Exception:
            gd = None
    return {"date": date, "items": get_game_totals_for_date(db, gd)}
