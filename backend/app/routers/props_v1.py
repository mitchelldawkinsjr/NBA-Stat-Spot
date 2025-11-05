from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/api/v1/props", tags=["props_v1"])

@router.get("/daily")
def daily_props(date: Optional[str] = None, min_confidence: Optional[float] = None):
    return {"items": []}

@router.get("/player/{player_id}")
def player_props(player_id: int, date: Optional[str] = None, game_id: Optional[str] = None):
    return {"items": []}

@router.get("/game/{game_id}")
def game_props(game_id: str):
    return {"items": []}

@router.get("/trending")
def trending_props(limit: int = 10):
    return {"items": []}

@router.get("/types")
def prop_types():
    return {"items": ["points", "rebounds", "assists", "3pm", "steals", "blocks"]}
