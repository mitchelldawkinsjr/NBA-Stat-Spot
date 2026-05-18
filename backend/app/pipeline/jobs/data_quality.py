"""Data quality checks after ingest/build."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from ...models.dashboard_snapshots import DashboardSnapshot
from ...models.games import Game
from ...models.player_game_stats import PlayerGameStat
from ...models.prediction_accuracy import PropPredictionRecord
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import pipeline_meta_repo


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    target = ctx.target_date or date.today()
    season = ctx.season or get_current_season()
    issues = []

    games_yesterday = (
        db.query(Game)
        .filter(Game.game_date == target - timedelta(days=1))
        .count()
    )
    if games_yesterday > 0:
        stats_count = (
            db.query(PlayerGameStat)
            .filter(PlayerGameStat.game_date == target - timedelta(days=1))
            .count()
        )
        if stats_count == 0:
            issues.append("no_player_stats_for_yesterday_games")

    pending_props = (
        db.query(PropPredictionRecord)
        .filter(
            PropPredictionRecord.record_date <= target - timedelta(days=1),
            PropPredictionRecord.actual_value.is_(None),
        )
        .count()
    )

    unpublished = (
        db.query(DashboardSnapshot)
        .filter(
            DashboardSnapshot.snapshot_date == target,
            DashboardSnapshot.is_published.is_(False),
        )
        .count()
    )

    result = {
        "target_date": target.isoformat(),
        "season": season,
        "games_yesterday": games_yesterday,
        "pending_prop_predictions": pending_props,
        "unpublished_snapshots_today": unpublished,
        "issues": issues,
        "ok": len(issues) == 0,
        "rows_written": 0,
    }
    if issues and not ctx.dry_run:
        raise RuntimeError(f"data_quality failed: {issues}")
    return result
