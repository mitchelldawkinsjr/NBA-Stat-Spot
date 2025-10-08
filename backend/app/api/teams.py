from fastapi import APIRouter
from typing import Dict

router = APIRouter(prefix="/api/teams", tags=["teams"])

@router.get("/{team_id}/defense")
def get_team_defense(team_id: int) -> Dict:
    # MVP stub values
    return {"teamId": team_id, "pace": 99.5, "defensiveRating": 112.3, "allowed": {"PTS": 1.0, "REB": 1.0, "AST": 1.0, "3PM": 1.0}}
