"""
Accuracy API - Historical accuracy for game predictions and AI pick of the day.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Query
from typing import Optional

from ..services.accuracy_tracking_service import get_accuracy_history

router = APIRouter(prefix="/api/v1/accuracy", tags=["accuracy_v1"])


@router.get(
    "/history",
    summary="Get prediction accuracy history",
    description="Returns historical accuracy for game predictions and AI pick of the day over a date range.",
)
def accuracy_history(
    from_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    days: int = Query(90, ge=1, le=365, description="Number of days to include (used if from_date not set)"),
):
    to_d = date.fromisoformat(to_date) if to_date else date.today()
    from_d = date.fromisoformat(from_date) if from_date else (to_d - timedelta(days=days))
    if from_d > to_d:
        from_d, to_d = to_d, from_d
    return get_accuracy_history(from_date=from_d, to_date=to_d, limit_days=days + (to_d - from_d).days)
