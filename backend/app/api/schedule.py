from fastapi import APIRouter
from typing import Dict, List

router = APIRouter(prefix="/api/schedule", tags=["schedule"])

@router.get("/upcoming")
def upcoming(hours: int = 24) -> Dict:
    try:
        # Try nba_api live scoreboard (today)
        from nba_api.live.nba.endpoints import scoreboard
        sb = scoreboard.ScoreBoard()
        games = []
        for g in sb.games.get_dict():
            games.append({"gameId": g.get("gameId"), "home": g.get("homeTeam", {}).get("teamTricode"), "away": g.get("awayTeam", {}).get("teamTricode"), "gameTimeUTC": g.get("gameTimeUTC")})
        return {"games": games}
    except Exception:
        # Fallback empty; good-bets endpoint will handle league-wide suggestions
        return {"games": []}
