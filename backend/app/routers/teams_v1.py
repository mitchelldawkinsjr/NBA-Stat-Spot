"""
Teams API Router - Team information and rosters
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ..services.nba_api_service import NBADataService
from ..services.team_player_service import TeamPlayerService

router = APIRouter(prefix="/api/v1/teams", tags=["teams_v1"])


@router.get("")
def list_teams():
    """List all NBA teams"""
    teams = NBADataService.fetch_all_teams()
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


@router.get("/{team_id}")
def get_team(team_id: int):
    """Get team details with roster"""
    teams = NBADataService.fetch_all_teams()
    team = next((t for t in teams if t.get("id") == team_id), None)
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Use TeamPlayerService to get roster
    roster = TeamPlayerService.get_players_for_team(team_id)
    
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


@router.get("/{team_id}/players")
def get_team_players(team_id: int):
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

