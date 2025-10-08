from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
from ..services.analytics import suggest_props_stub

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
    from ..services.analytics import suggest_from_gamelogs
    return {"suggestions": suggest_from_gamelogs(req.playerId, req.season, req.lastN, req.marketLines)}

@router.post("/good-bets")
def good_bets(hours: int = 24) -> Dict:
    return {"games": []}
