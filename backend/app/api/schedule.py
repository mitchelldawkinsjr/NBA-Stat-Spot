from fastapi import APIRouter
from typing import Dict, List
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/schedule", tags=["schedule"])

@router.get("/upcoming")
def upcoming(hours: int = 24) -> Dict:
    """
    DEPRECATED: This endpoint is deprecated. Use /api/v1/games/upcoming instead.
    This endpoint will be removed in a future version.
    """
    logger.warning("Legacy endpoint accessed", endpoint="/api/schedule/upcoming", hours=hours)
    try:
        # Try nba_api live scoreboard (today)
        from nba_api.live.nba.endpoints import scoreboard
        sb = scoreboard.ScoreBoard()
        games = []
        for g in sb.games.get_dict():
            games.append({"gameId": g.get("gameId"), "home": g.get("homeTeam", {}).get("teamTricode"), "away": g.get("awayTeam", {}).get("teamTricode"), "gameTimeUTC": g.get("gameTimeUTC")})
        return {
            "games": games,
            "deprecated": True,
            "message": "Use /api/v1/games/upcoming instead"
        }
    except Exception:
        # Fallback empty; good-bets endpoint will handle league-wide suggestions
        return {
            "games": [],
            "deprecated": True,
            "message": "Use /api/v1/games/upcoming instead"
        }
