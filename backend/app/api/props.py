from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from ..services.analytics import suggest_from_gamelogs

router = APIRouter(prefix="/api/props", tags=["props"])

class SuggestRequest(BaseModel):
    playerId: int
    season: str | None = None
    lastN: int | None = None
    home: bool | None = None
    opponentId: int | None = None
    marketLines: Dict[str, float] | None = None

@router.post("/suggest")
def suggest(req: SuggestRequest) -> Dict:
    return {"suggestions": suggest_from_gamelogs(req.playerId, req.season, req.lastN, req.marketLines)}

@router.post("/good-bets")
def good_bets(hours: int = 24) -> Dict:
    # MVP: featured players across league until robust schedule-level joining
    featured_player_ids = [2544, 201939, 203507, 1629029, 203076]
    games: List[Dict] = []
    top: List[Dict] = []
    for pid in featured_player_ids:
        try:
            sugs = suggest_from_gamelogs(pid, None, 10, None)
            sugs_sorted = sorted(sugs, key=lambda s: (s.get("confidence") or 0), reverse=True)
            top.append({"playerId": pid, "suggestions": sugs_sorted[:3]})
        except Exception:
            continue
    games.append({"game": {"desc": "Featured Top Players"}, "top": top})
    return {"games": games}
