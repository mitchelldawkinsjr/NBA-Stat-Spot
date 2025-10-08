from fastapi import APIRouter, Query
from typing import List
from ..core.models import Player

router = APIRouter(prefix="/api/players", tags=["players"])

@router.get("/search")
def search_players(q: str = Query(..., min_length=1)) -> dict:
    # MVP stub: static few players for dev
    sample = [
        Player(id=2544, name="LeBron James", team="LAL"),
        Player(id=201939, name="Stephen Curry", team="GSW"),
        Player(id=203507, name="Giannis Antetokounmpo", team="MIL"),
    ]
    items = [p for p in sample if q.lower() in p.name.lower()]
    return {"items": [p.model_dump() for p in items]}
