"""
Teams API Router - Team information and rosters
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ..services.nba_api_service import NBADataService

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
    
    # Get all players and filter by team_id
    all_players = NBADataService.fetch_all_players_including_rookies()
    roster = []
    
    for p in all_players:
        player_team_id = p.get("team_id")
        if player_team_id is None:
            continue
        
        # Handle both int and string comparisons
        try:
            # Try integer comparison first
            if int(player_team_id) == int(team_id):
                roster.append({
                    "id": p.get("id"),
                    "name": p.get("full_name"),
                    "position": p.get("position"),
                    "jersey_number": p.get("jersey_number"),
                })
        except (ValueError, TypeError):
            # Fallback to direct comparison if conversion fails
            if player_team_id == team_id:
                roster.append({
                    "id": p.get("id"),
                    "name": p.get("full_name"),
                    "position": p.get("position"),
                    "jersey_number": p.get("jersey_number"),
                })
    
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
        all_players = NBADataService.fetch_all_players_including_rookies()
        if not all_players:
            return {"items": [], "team_id": team_id, "total": 0, "error": "No players found in database"}
        
        players = []
        
        # Normalize team_id to int for comparison
        team_id_int = int(team_id)
        
        # Debug: count players with team_id
        players_with_team = [p for p in all_players if p.get("team_id") is not None]
        
        for p in all_players:
            player_team_id = p.get("team_id")
            if player_team_id is None:
                continue
            
            # Handle both int and string comparisons
            try:
                # Try integer comparison first
                player_team_id_int = int(player_team_id)
                if player_team_id_int == team_id_int:
                    players.append({
                        "id": p.get("id"),
                        "name": p.get("full_name"),
                        "position": p.get("position"),
                        "jersey_number": p.get("jersey_number"),
                    })
            except (ValueError, TypeError):
                # Fallback to direct comparison if conversion fails
                if player_team_id == team_id or player_team_id == team_id_int:
                    players.append({
                        "id": p.get("id"),
                        "name": p.get("full_name"),
                        "position": p.get("position"),
                        "jersey_number": p.get("jersey_number"),
                    })
        
        return {
            "items": players, 
            "team_id": team_id, 
            "total": len(players),
            "debug": {
                "total_players": len(all_players),
                "players_with_team_id": len(players_with_team),
                "requested_team_id": team_id_int
            }
        }
    except Exception as e:
        return {
            "items": [], 
            "team_id": team_id, 
            "total": 0, 
            "error": str(e)
        }

