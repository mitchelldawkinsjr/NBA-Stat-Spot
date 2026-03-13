"""
Insights API - Daily rule-based matchup and pace insights.
"""
from fastapi import APIRouter, Query
from typing import Optional

from ..services.insight_scanner import scan_all_insights

router = APIRouter(prefix="/api/v1/insights", tags=["insights_v1"])


@router.get(
    "/daily",
    summary="Get daily insights",
    description="Returns rule-based insights for today's games (e.g. team allows 2nd most PTS to PGs, top pace).",
)
def get_daily_insights(
    date: Optional[str] = Query(None, description="Date YYYY-MM-DD (default: today)"),
    season: Optional[str] = Query(None, description="Season (default: current)"),
    limit: int = Query(50, ge=1, le=100, description="Max number of insights"),
):
    alerts = scan_all_insights(date_str=date, season=season, limit=limit)
    return {
        "items": [
            {
                "text": a.text,
                "category": a.category,
                "team_abbr": a.team_abbr,
                "stat": a.stat,
                "rank": a.rank,
                "position": a.position,
            }
            for a in alerts
        ],
        "count": len(alerts),
    }
