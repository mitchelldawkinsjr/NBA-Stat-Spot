"""Settle open accuracy predictions using DB stats.

Backfills missing game logs for pending prop players first, then grades
predictions. Rows that still cannot be matched (DNP / no game) are voided
so they leave the pending queue without polluting hit rates.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...models.prediction_accuracy import PropPredictionRecord
from ...services.accuracy_tracking_service import settle_open_predictions
from ...utils.season import get_current_season
from ..context import PipelineContext
from . import backfill_settlement_stats as backfill_job


def _void_unresolvable(db: Session, target: date) -> int:
    """Mark remaining open props as void after backfill+settle (no matching game)."""
    rows = (
        db.query(PropPredictionRecord)
        .filter(
            PropPredictionRecord.record_date <= target,
            PropPredictionRecord.actual_value.is_(None),
            PropPredictionRecord.settled_at.is_(None),
        )
        .all()
    )
    n = 0
    for r in rows:
        ver = (r.model_version or "").strip()
        r.model_version = (ver + "|void:no_game").strip("|")[:64]
        r.settled_at = datetime.utcnow()
        n += 1
    if n:
        db.flush()
    return n


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    target = ctx.target_date or (date.today() - timedelta(days=1))
    void_missing = bool(ctx.stats.get("void_missing", True))

    backfill = backfill_job.run(
        PipelineContext(
            job_name="backfill_settlement_stats",
            target_date=target,
            season=season,
            dry_run=ctx.dry_run,
            run_id=ctx.run_id,
        ),
        db,
    )

    from ...services.stats_provider import DbStatsProvider

    result = settle_open_predictions(target, season=season, stats_provider=DbStatsProvider())

    voided = 0
    if void_missing and not ctx.dry_run:
        voided = _void_unresolvable(db, target)

    pending_left = (
        db.query(PropPredictionRecord)
        .filter(
            PropPredictionRecord.actual_value.is_(None),
            PropPredictionRecord.settled_at.is_(None),
        )
        .count()
    )

    return {
        "rows_written": int(result.get("count_dates", 0) or 0)
        + int(backfill.get("players_filled", 0) or 0),
        "target_date": target.isoformat(),
        "backfill": backfill,
        "result": result,
        "voided_no_game": voided,
        "pending_left": pending_left,
    }
