"""Settle open accuracy predictions using DB stats."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...services.accuracy_tracking_service import settle_open_predictions
from ...utils.season import get_current_season
from ..context import PipelineContext


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    target = ctx.target_date or (date.today() - timedelta(days=1))

    from ...services.stats_provider import DbStatsProvider

    result = settle_open_predictions(target, season=season, stats_provider=DbStatsProvider())
    return {
        "rows_written": result.get("count_dates", 0),
        "target_date": target.isoformat(),
        "result": result,
    }
