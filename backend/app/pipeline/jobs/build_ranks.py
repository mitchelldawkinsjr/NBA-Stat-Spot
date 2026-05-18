"""Build team rank caches (defensive/offensive/pace) via existing admin refresh logic."""
from __future__ import annotations
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...services.cache_service import get_cache_service
from ...services.context_collector import ContextCollector
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories.snapshots_repo import ARTIFACT_TEAM_RANKS, save_snapshot
from ..config import pipeline_shadow_build, pipeline_auto_publish


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    target = ctx.target_date
    if not target:
        from datetime import date
        target = date.today()

    cache = get_cache_service()
    def_ranks = ContextCollector.get_cached_defensive_ranks(season) or ContextCollector._calculate_defensive_ranks(season)
    off_ranks = ContextCollector.get_cached_offensive_ranks(season) or ContextCollector._calculate_offensive_ranks(season)
    pace_ranks = ContextCollector.get_cached_pace_ranks(season) or ContextCollector._calculate_pace_ranks(season)

    payload = {
        "defensive_ranks": def_ranks,
        "offensive_ranks": off_ranks,
        "pace_ranks": pace_ranks,
        "season": season,
    }

    publish = pipeline_auto_publish() and not pipeline_shadow_build()
    save_snapshot(
        db,
        snapshot_date=target,
        artifact_type=ARTIFACT_TEAM_RANKS,
        season=season,
        payload=payload,
        pipeline_run_id=ctx.run_id,
        publish=publish,
    )

    cache.set(f"defensive_ranks:{season}", def_ranks, ttl=86400)
    cache.set(f"offensive_ranks:{season}", off_ranks, ttl=86400)
    cache.set(f"pace_ranks:{season}", pace_ranks, ttl=86400)

    return {"rows_written": 1, "season": season, "published": publish}
