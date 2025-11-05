from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/players", tags=["players_v1"])

@router.get("/search")
def search(q: str):
    return {"items": []}

@router.get("/{player_id}")
def detail(player_id: int):
    return {"player": {"id": player_id}}

@router.get("/{player_id}/stats")
def stats(player_id: int, games: int = 10):
    return {"items": []}

@router.get("/{player_id}/trends")
def trends(player_id: int, stat_type: str):
    return {"items": []}

@router.get("/featured")
def featured():
    return {"items": []}
