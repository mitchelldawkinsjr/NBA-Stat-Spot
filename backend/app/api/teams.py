from fastapi import APIRouter
from typing import Dict
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/teams", tags=["teams"])

@router.get("/{team_id}/defense")
def get_team_defense(team_id: int) -> Dict:
    """
    DEPRECATED: This endpoint is deprecated. Use /api/v1/teams/{team_id} instead.
    This endpoint will be removed in a future version.
    """
    logger.warning("Legacy endpoint accessed", endpoint=f"/api/teams/{team_id}/defense", team_id=team_id)
    # MVP stub values
    return {
        "teamId": team_id, 
        "pace": 99.5, 
        "defensiveRating": 112.3, 
        "allowed": {"PTS": 1.0, "REB": 1.0, "AST": 1.0, "3PM": 1.0},
        "deprecated": True,
        "message": f"Use /api/v1/teams/{team_id} instead"
    }
