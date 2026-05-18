"""Aggregated dashboard read API (pipeline snapshots)."""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query

from ..pipeline.config import pipeline_read_dashboard
from ..services.snapshot_service import home_dashboard_payload

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard_v1"])


@router.get("/home")
def dashboard_home(
    date_param: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD"),
):
    target = (
        date.fromisoformat(date_param[:10])
        if date_param
        else date.today()
    )
    if pipeline_read_dashboard():
        payload = home_dashboard_payload(target)
        if payload:
            return payload
    return {
        "date": target.isoformat(),
        "top_picks": None,
        "daily_props": None,
        "pick_of_the_day": None,
        "data_as_of": None,
        "source": "live",
        "message": "No published snapshot; use props endpoints or enable pipeline build.",
    }
