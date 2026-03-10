"""
Teams API Router - Team information and rosters
"""
import structlog
from fastapi import APIRouter, HTTPException, Path, Query
from typing import List, Dict, Any, Optional
from ..services.nba_api_service import NBADataService
from ..services.team_player_service import TeamPlayerService
from ..services.context_collector import ContextCollector

router = APIRouter(prefix="/api/v1/teams", tags=["teams_v1"])
logger = structlog.get_logger()


@router.get(
    "",
    summary="List all NBA teams",
    description="Get a list of all NBA teams with basic information including team ID, name, abbreviation, city, conference, and division.",
    response_description="List of all NBA teams",
    tags=["teams_v1"]
)
def list_teams():
    """List all NBA teams"""
    try:
        teams = NBADataService.fetch_all_teams() or []
    except Exception as e:
        logger.error("teams list failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Teams data temporarily unavailable. Try again shortly.",
        )
    return {
        "items": [
            {
                "id": t.get("id"),
                "full_name": t.get("full_name"),
                "abbreviation": t.get("abbreviation"),
                "city": t.get("city"),
                "nickname": t.get("nickname"),
                "conference": t.get("conference"),
                "division": t.get("division"),
            }
            for t in teams
        ]
    }


@router.get(
    "/team-stats/ranks",
    summary="Get team defense and offense ranks",
    description="Returns defensive and offensive rankings (PTS, REB, AST, 3PM) for all teams. Defense = what team allows (lower rank = better D). Offense = what team scores (rank 1 = best).",
    response_description="List of teams with def/off ranks",
    tags=["teams_v1"]
)
def get_team_stats_ranks(
    season: Optional[str] = Query("2025-26", description="Season (e.g. 2025-26)")
):
    """Get team-level defense and offense ranks for all teams."""
    try:
        teams = NBADataService.fetch_all_teams() or []
        def_ranks = ContextCollector._calculate_defensive_ranks(season or "2025-26")
        off_ranks = ContextCollector._calculate_offensive_ranks(season or "2025-26")
        items = []
        for t in teams:
            team_id = t.get("id")
            if team_id is None:
                continue
            d = def_ranks.get(team_id) or {}
            o = off_ranks.get(team_id) or {}
            items.append({
                "id": team_id,
                "abbreviation": t.get("abbreviation"),
                "full_name": t.get("full_name"),
                "def_rank_pts": d.get("pts"),
                "def_rank_reb": d.get("reb"),
                "def_rank_ast": d.get("ast"),
                "def_rank_3pm": d.get("3pm"),
                "off_rank_pts": o.get("pts"),
                "off_rank_reb": o.get("reb"),
                "off_rank_ast": o.get("ast"),
                "off_rank_3pm": o.get("3pm"),
            })
        return {"season": season or "2025-26", "items": items}
    except Exception as e:
        logger.error("team-stats ranks failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Team stats temporarily unavailable. Try again shortly.",
        )


@router.get(
    "/{team_id}",
    summary="Get team details with roster",
    description="Get detailed information about a specific team including roster of players.",
    response_description="Team information with roster",
    tags=["teams_v1"]
)
def get_team(
    team_id: int = Path(..., description="NBA team ID", example=1610612744)
):
    """Get team details with roster"""
    try:
        teams = NBADataService.fetch_all_teams() or []
        roster = TeamPlayerService.get_players_for_team(team_id)
    except Exception as e:
        logger.error("get_team failed", team_id=team_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Team data temporarily unavailable. Try again shortly.",
        )
    team = next((t for t in teams if t.get("id") == team_id), None)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return {
        "team": {
            "id": team.get("id"),
            "full_name": team.get("full_name"),
            "abbreviation": team.get("abbreviation"),
            "city": team.get("city"),
            "nickname": team.get("nickname"),
            "conference": team.get("conference"),
            "division": team.get("division"),
        },
        "roster": roster,
        "roster_count": len(roster)
    }


@router.get(
    "/{team_id}/players",
    summary="Get team roster",
    description="Get the complete roster of players for a specific team.",
    response_description="List of players on the team",
    tags=["teams_v1"]
)
def get_team_players(
    team_id: int = Path(..., description="NBA team ID", example=1610612744)
):
    """Get players for a specific team"""
    try:
        # Use TeamPlayerService to get players
        players = TeamPlayerService.get_players_for_team(team_id)
        
        # Get debug info
        all_players = NBADataService.fetch_all_players_including_rookies()
        players_with_team = [p for p in all_players if TeamPlayerService.normalize_team_id(p.get("team_id")) is not None]
        
        return {
            "items": players, 
            "team_id": team_id, 
            "total": len(players),
            "debug": {
                "total_players": len(all_players) if all_players else 0,
                "players_with_team_id": len(players_with_team),
                "requested_team_id": team_id,
                "normalized_team_id": TeamPlayerService.normalize_team_id(team_id)
            }
        }
    except Exception as e:
        return {
            "items": [], 
            "team_id": team_id, 
            "total": 0, 
            "error": str(e)
        }

