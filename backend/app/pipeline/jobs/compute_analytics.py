"""Precompute player_stat_windows and player_line_hit_rates from validated game stats."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...models.player_game_stats import PlayerGameStat
from ...models.player_line_hit_rates import PlayerLineHitRate
from ...models.player_stat_windows import PlayerStatWindow
from ...services.analytics_constants import FORMULA_VERSION, STAT_TYPES, WINDOWS
from ...services.box_score_validator import BoxScoreValidator
from ...services.prop_engine import PropBetEngine
from ...services.stats_calculator import StatsCalculator
from ...utils.season import get_current_season
from ..context import PipelineContext


def _row_to_log(r: PlayerGameStat) -> Dict[str, Any]:
    return {
        "game_id": r.game_id,
        "game_date": r.game_date.isoformat() if r.game_date else "",
        "matchup": "",
        "pts": float(r.points or 0),
        "reb": float(r.rebounds or 0),
        "ast": float(r.assists or 0),
        "tpm": float(r.three_pointers_made or 0),
        "minutes": float(r.minutes_played or 0),
        "stl": float(r.steals or 0),
        "blk": float(r.blocks or 0),
        "tov": float(r.turnovers or 0),
    }


def _logs_for_player(db: Session, player_id: int, season: str) -> List[Dict[str, Any]]:
    from sqlalchemy import or_

    rows = (
        db.query(PlayerGameStat)
        .filter(
            PlayerGameStat.player_id == player_id,
            PlayerGameStat.season == season,
            or_(
                PlayerGameStat.validation_status.is_(None),
                PlayerGameStat.validation_status != BoxScoreValidator.STATUS_INVALID,
            ),
        )
        .order_by(PlayerGameStat.game_date.asc())
        .all()
    )
    return [_row_to_log(r) for r in rows]


def _window_slice(logs: List[Dict[str, Any]], window_key: str) -> List[Dict[str, Any]]:
    n = WINDOWS[window_key]
    if n is None:
        return logs
    return logs[-n:] if len(logs) >= n else logs


def _upsert_window(
    db: Session,
    *,
    player_id: int,
    season: str,
    stat_type: str,
    window: str,
    logs: List[Dict[str, Any]],
    pipeline_run_id: Optional[int],
) -> None:
    n = WINDOWS[window]
    sample = logs if n is None else (logs[-n:] if len(logs) >= n else logs)
    games_sample = len(sample)
    if games_sample == 0:
        return

    form = StatsCalculator.calculate_recent_form(
        logs, stat_type, n_games=n if n else len(logs)
    )
    avg = StatsCalculator.calculate_rolling_average(
        logs, stat_type, n_games=n if n else len(logs)
    )
    consistency = StatsCalculator.calculate_consistency(
        logs, stat_type, n_games=min(n or len(logs), len(logs))
    )
    heat = StatsCalculator.calculate_heat_index(
        logs, stat_type, n_games=min(n or 10, len(logs)) if n else min(10, len(logs))
    )
    vol = StatsCalculator.calculate_volatility_index(
        logs, stat_type, n_games=min(n or 10, len(logs)) if n else min(10, len(logs))
    )

    row = (
        db.query(PlayerStatWindow)
        .filter_by(player_id=player_id, season=season, stat_type=stat_type, window=window)
        .first()
    )
    if not row:
        row = PlayerStatWindow(
            player_id=player_id, season=season, stat_type=stat_type, window=window
        )
        db.add(row)

    row.avg = round(avg, 4)
    row.weighted_avg = round(float(form.get("weighted_avg") or 0), 4)
    row.trend = form.get("trend")
    row.trend_slope = round(float(form.get("trend_slope") or 0), 4)
    row.consistency = round(consistency, 4)
    row.heat_index = round(heat, 4)
    row.volatility_index = round(vol, 4) if isinstance(vol, float) else vol
    row.games_sample = games_sample
    row.formula_version = FORMULA_VERSION
    row.computed_at = datetime.utcnow()
    row.pipeline_run_id = pipeline_run_id


def _upsert_hit_rate(
    db: Session,
    *,
    player_id: int,
    season: str,
    stat_type: str,
    line: float,
    direction: str,
    window: str,
    logs: List[Dict[str, Any]],
    pipeline_run_id: Optional[int],
) -> None:
    n = WINDOWS[window]
    slice_logs = _window_slice(logs, window)
    if not slice_logs:
        return
    period = StatsCalculator.trend_period(
        logs, line, stat_type, direction, n_games=n if n else len(logs)
    )
    row = (
        db.query(PlayerLineHitRate)
        .filter_by(
            player_id=player_id,
            season=season,
            stat_type=stat_type,
            line=line,
            direction=direction,
            window=window,
        )
        .first()
    )
    if not row:
        row = PlayerLineHitRate(
            player_id=player_id,
            season=season,
            stat_type=stat_type,
            line=line,
            direction=direction,
            window=window,
        )
        db.add(row)

    row.hit_rate = round(period["hits"] / period["total"], 4) if period.get("total") else 0.0
    row.hits = int(period.get("hits") or 0)
    row.total = int(period.get("total") or 0)
    row.formula_version = FORMULA_VERSION
    row.computed_at = datetime.utcnow()
    row.pipeline_run_id = pipeline_run_id


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    run_id = ctx.run_id

    player_ids = [
        r[0]
        for r in db.query(PlayerGameStat.player_id)
        .filter(PlayerGameStat.season == season)
        .distinct()
        .all()
    ]

    windows_written = 0
    hit_rates_written = 0
    players_processed = 0
    skipped_empty = 0

    CHUNK = 100
    for i in range(0, len(player_ids), CHUNK):
        chunk = player_ids[i : i + CHUNK]
        for player_id in chunk:
            logs = _logs_for_player(db, player_id, season)
            if len(logs) < 3:
                skipped_empty += 1
                continue
            players_processed += 1
            for stat_type in STAT_TYPES:
                fair_line = PropBetEngine.determine_line_value(logs, stat_type)
                for window in WINDOWS:
                    _upsert_window(
                        db,
                        player_id=player_id,
                        season=season,
                        stat_type=stat_type,
                        window=window,
                        logs=logs,
                        pipeline_run_id=run_id,
                    )
                    windows_written += 1
                    for direction in ("over", "under"):
                        _upsert_hit_rate(
                            db,
                            player_id=player_id,
                            season=season,
                            stat_type=stat_type,
                            line=fair_line,
                            direction=direction,
                            window=window,
                            logs=logs,
                            pipeline_run_id=run_id,
                        )
                        hit_rates_written += 1
        db.flush()

    return {
        "rows_written": windows_written + hit_rates_written,
        "windows_written": windows_written,
        "hit_rates_written": hit_rates_written,
        "players_processed": players_processed,
        "players_skipped": skipped_empty,
        "season": season,
        "formula_version": FORMULA_VERSION,
    }
