from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

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
    # MVP: return empty suggestions; analytics service will fill later
    return {"suggestions": []}

@router.post("/good-bets")
def good_bets(hours: int = 24) -> Dict:
    return {"games": []}
