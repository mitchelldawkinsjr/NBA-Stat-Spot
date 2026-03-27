from typing import Optional

from fastapi import APIRouter, Query, Request

from ..core.rate_limiter import limiter
from ..services.live_props_service import get_live_props_dashboard

router = APIRouter(prefix="/api/v1/live-props", tags=["live_props_v1"])


@router.get("/dashboard")
@limiter.limit("30/minute")
def live_props_dashboard(
    request: Request,
    game_id: Optional[str] = Query(
        None,
        description="ESPN-style game id. Defaults to first non-final game on today's slate.",
    ),
    season: Optional[str] = Query(None, description="Season e.g. 2025-26"),
    live_box: bool = Query(
        True,
        description="When false, skips ESPN box fetch (progression uses 0s in-game); faster for phased loads.",
    ),
    skip_cache: bool = Query(
        False,
        description="When true, bypasses the 25s in-memory dashboard response cache.",
    ),
):
    """
    Aggregated payload for the Live Prop Dashboard: today's games, selected game,
    per-player PTS fair line, L5/L10/L20 hit trends, live box stats (one ESPN summary per game),
    mock odds, confidence cards.
    """
    return get_live_props_dashboard(
        game_id=game_id,
        season=season,
        include_live_box=live_box,
        use_response_cache=not skip_cache,
    )
