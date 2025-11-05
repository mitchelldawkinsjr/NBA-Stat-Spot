from fastapi import APIRouter
from typing import Optional, List, Dict
from ..services.nba_api_service import NBADataService
from ..services.prop_engine import PropBetEngine
from ..services.prop_filter import PropFilter

router = APIRouter(prefix="/api/v1/props", tags=["props_v1"])

STAT_KEYS = ["pts", "reb", "ast", "tpm"]


def build_suggestions_for_player(player_id: int, season: Optional[str]) -> List[Dict]:
    logs = NBADataService.fetch_player_game_log(player_id, season)
    suggestions: List[Dict] = []
    for sk in STAT_KEYS:
        line = PropBetEngine.determine_line_value(logs, sk)
        suggestions.append(PropBetEngine.evaluate_prop(logs, sk, line))
    return suggestions

@router.get("/daily")
def daily_props(date: Optional[str] = None, min_confidence: Optional[float] = None):
    featured = [2544, 201939, 203507, 1629029, 203076]
    items: List[Dict] = []
    for pid in featured:
        try:
            sugs = build_suggestions_for_player(pid, None)
            if min_confidence:
                sugs = PropFilter.filter_by_confidence(sugs, min_confidence)
            for s in sugs:
                s.update({"playerId": pid})
            items.extend(sugs)
        except Exception:
            continue
    items = PropFilter.rank_suggestions(items, "confidence")
    return {"items": items}

@router.get("/player/{player_id}")
def player_props(player_id: int, date: Optional[str] = None, season: Optional[str] = None):
    sugs = build_suggestions_for_player(player_id, season)
    return {"items": sugs}

@router.get("/game/{game_id}")
def game_props(game_id: str):
    return {"items": []}

@router.get("/trending")
def trending_props(limit: int = 10):
    items = daily_props().get("items", [])[:limit]
    return {"items": items}

@router.get("/types")
def prop_types():
    return {"items": ["points", "rebounds", "assists", "3pm", "steals", "blocks"]}
