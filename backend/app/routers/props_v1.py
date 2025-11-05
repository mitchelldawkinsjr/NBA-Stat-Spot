from fastapi import APIRouter
from pydantic import BaseModel
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


class PlayerSuggestRequest(BaseModel):
    playerId: int
    season: Optional[str] = None
    lastN: Optional[int] = None
    home: Optional[str] = None  # 'home' | 'away' | None
    marketLines: Optional[Dict[str, float]] = None  # e.g., {"PTS": 24.5}

@router.post("/player")
def suggest_player_props(req: PlayerSuggestRequest):
    # Default season fallback
    season = req.season or "2025-26"
    try:
        logs = NBADataService.fetch_player_game_log(req.playerId, season)
    except Exception:
        # Gracefully degrade instead of 500
        return {"suggestions": []}
    # Optional venue filter
    if req.home in ("home", "away"):
        is_home = req.home == "home"
        filtered: List[Dict] = []
        for g in logs:
            matchup = (g.get("matchup") or "").lower()
            at_away = "@" in matchup
            vs_home = "vs" in matchup
            if is_home and vs_home:
                filtered.append(g)
            elif (not is_home) and at_away:
                filtered.append(g)
        logs = filtered
    # Optional lastN slice
    if req.lastN and req.lastN > 0:
        logs = logs[-req.lastN:]
    # Enrich PRA
    for g in logs:
        g["pra"] = float(g.get("pts", 0) or 0) + float(g.get("reb", 0) or 0) + float(g.get("ast", 0) or 0)

    suggestions: List[Dict] = []
    lines = req.marketLines or {}
    # Map display -> stat key
    key_map = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm", "PRA": "pra"}
    for disp_key, market_line in lines.items():
        stat_key = key_map.get(disp_key)
        if stat_key is None:
            continue
        try:
            fair = PropBetEngine.determine_line_value(logs, stat_key)
            ev = PropBetEngine.evaluate_prop(logs, stat_key, float(market_line))
            suggestions.append({
                "type": disp_key,
                "marketLine": float(market_line),
                "fairLine": float(fair),
                "confidence": ev.get("confidence"),
                "rationale": [ev.get("rationale", {}).get("summary", "Based on recent form and hit rate")],
            })
        except Exception:
            continue
    return {"suggestions": suggestions}

@router.get("/daily")
def daily_props(date: Optional[str] = None, min_confidence: Optional[float] = None, limit: int = 50):
    # Determine today's teams from live scoreboard
    try:
        games = NBADataService.fetch_todays_games()
    except Exception:
        games = []

    team_abbrs = set()
    for g in games:
        if g.get("home"):
            team_abbrs.add(g.get("home"))
        if g.get("away"):
            team_abbrs.add(g.get("away"))

    items: List[Dict] = []
    if team_abbrs:
        # Map abbr -> team id
        teams = NBADataService.fetch_all_teams() or []
        abbr_to_id = {t.get("abbreviation"): t.get("id") for t in teams}
        team_ids_today = {abbr_to_id.get(ab) for ab in team_abbrs if ab in abbr_to_id}

        # Filter active players on today's teams
        active = NBADataService.fetch_active_players() or []
        todays_players = [p for p in active if p.get("team_id") in team_ids_today]

        # Limit to reasonable number
        todays_players = todays_players[:60]

        for p in todays_players:
            pid = p.get("id")
            pname = p.get("full_name")
            try:
                sugs = build_suggestions_for_player(int(pid), "2025-26")
                if min_confidence:
                    sugs = PropFilter.filter_by_confidence(sugs, min_confidence)
                for s in sugs:
                    s.update({"playerId": pid, "playerName": pname})
                items.extend(sugs)
            except Exception:
                continue
    else:
        # Fallback to a small featured set if no games found
        featured = [2544, 201939, 203507, 1629029, 203076]
        for pid in featured:
            try:
                sugs = build_suggestions_for_player(pid, "2025-26")
                if min_confidence:
                    sugs = PropFilter.filter_by_confidence(sugs, min_confidence)
                for s in sugs:
                    s.update({"playerId": pid})
                items.extend(sugs)
            except Exception:
                continue

    items = PropFilter.rank_suggestions(items, "confidence")[: max(1, limit)]
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
