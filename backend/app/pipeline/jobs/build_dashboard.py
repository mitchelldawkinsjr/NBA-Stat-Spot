"""Build dashboard snapshots and record accuracy rows."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ...services.accuracy_tracking_service import record_pick_of_the_day, record_prop_predictions
from ...services.best_picks_service import BestPicksService
from ...services.cache_service import get_cache_service
from ...services.daily_props_service import DailyPropsService
from ...utils.season import get_current_season
from ..config import pipeline_auto_publish, pipeline_shadow_build
from ..context import PipelineContext
from ..repositories.snapshots_repo import (
    ARTIFACT_DAILY_PROPS,
    ARTIFACT_PICK_OF_DAY,
    ARTIFACT_TOP_PICKS,
    save_snapshot,
)
from . import data_quality as dq_job


def _derive_pick_of_day(items: List[Dict[str, Any]], today_str: str) -> Dict[str, Any]:
    filtered = [
        i
        for i in items
        if (i.get("gameDate") or i.get("game_date") or "").startswith(today_str[:10])
    ]
    if not filtered:
        return {}
    filtered.sort(key=lambda x: (x.get("confidence") or 0), reverse=True)
    top = filtered[0]
    return {
        "playerId": top.get("playerId"),
        "playerName": top.get("playerName"),
        "type": top.get("type"),
        "marketLine": top.get("marketLine") or top.get("fairLine"),
        "fairLine": top.get("fairLine"),
        "suggestion": top.get("suggestion", "over"),
        "confidence": top.get("confidence"),
        "rationale": top.get("rationale"),
        "gameDate": top.get("gameDate") or top.get("game_date"),
        "confidenceSource": top.get("confidenceSource"),
        "rationaleSource": top.get("rationaleSource"),
        "mlAvailable": top.get("mlAvailable"),
    }


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    snapshot_date = ctx.target_date or date.today()
    ds = snapshot_date.isoformat()
    publish = pipeline_auto_publish() and not pipeline_shadow_build()

    daily = DailyPropsService.get_top_props_for_date(
        date=ds, season=season, min_confidence=50.0, limit=100
    )
    top = BestPicksService.get_top_picks(date=ds, season=season, limit=12, min_confidence=62.0)
    pick = _derive_pick_of_day(daily.get("items") or [], ds)

    save_snapshot(
        db,
        snapshot_date=snapshot_date,
        artifact_type=ARTIFACT_DAILY_PROPS,
        season=season,
        payload=daily,
        pipeline_run_id=ctx.run_id,
        publish=publish,
    )
    save_snapshot(
        db,
        snapshot_date=snapshot_date,
        artifact_type=ARTIFACT_TOP_PICKS,
        season=season,
        payload=top,
        pipeline_run_id=ctx.run_id,
        publish=publish,
    )
    if pick:
        save_snapshot(
            db,
            snapshot_date=snapshot_date,
            artifact_type=ARTIFACT_PICK_OF_DAY,
            season=season,
            payload=pick,
            pipeline_run_id=ctx.run_id,
            publish=publish,
        )

    if publish:
        record_prop_predictions(snapshot_date, top.get("items") or [])
        if pick:
            record_pick_of_the_day(snapshot_date, pick)

    cache = get_cache_service()
    cache.set(f"daily_props:{ds}", daily, ttl=86400)
    cache.set(f"top_picks:{ds}", top, ttl=86400)
    if pick:
        cache.set(f"pick_of_the_day:{ds}", pick, ttl=86400)

    dq_ctx = PipelineContext(
        job_name="data_quality",
        target_date=snapshot_date,
        season=season,
        dry_run=False,
        run_id=ctx.run_id,
    )
    if publish:
        try:
            dq_job.run(dq_ctx, db)
        except RuntimeError:
            raise

    return {
        "rows_written": 3,
        "snapshot_date": ds,
        "top_picks_count": len(top.get("items") or []),
        "daily_props_count": len(daily.get("items") or []),
        "published": publish,
    }
