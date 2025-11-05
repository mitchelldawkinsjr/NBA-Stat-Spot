from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])

@router.get("/today")
def today():
    return {"games": []}

@router.get("/upcoming")
def upcoming(days: int = 7):
    return {"games": []}

@router.get("/{game_id}")
def game_detail(game_id: str):
    return {"game": {"id": game_id}}
