"""Backfill player game logs needed to settle open prop predictions."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy.orm import Session

from ...models.prediction_accuracy import PropPredictionRecord
from ...services.espn_game_log import fetch_player_game_log_espn
from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import player_stats_repo

# Cover regular season + playoffs for settlement matching.
_ESPN_LIMIT = 90


def _pending_player_ids(db: Session) -> List[int]:
    rows = (
        db.query(PropPredictionRecord.player_id)
        .filter(
            PropPredictionRecord.actual_value.is_(None),
            PropPredictionRecord.settled_at.is_(None),
        )
        .distinct()
        .all()
    )
    return [int(r[0]) for r in rows if r[0] is not None]


def _fetch_one(pid: int, season: str) -> Tuple[int, List[Dict[str, Any]], str]:
    try:
        logs = fetch_player_game_log_espn(pid, season, limit=_ESPN_LIMIT) or []
        if NBADataService._is_good_game_log(logs):
            return pid, logs, "espn"
    except Exception:
        pass
    try:
        logs = NBADataService.fetch_player_game_log(pid, season, force_refresh=True) or []
        if NBADataService._is_good_game_log(logs):
            return pid, logs, "nba_api"
    except Exception:
        pass
    return pid, [], "fail"


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    player_ids = _pending_player_ids(db)
    if not player_ids:
        return {
            "rows_written": 0,
            "players_targeted": 0,
            "players_filled": 0,
            "errors": 0,
            "season": season,
        }

    filled = 0
    errors = 0
    sources: Dict[str, int] = {"espn": 0, "nba_api": 0, "fail": 0}
    results: List[Tuple[int, List[Dict[str, Any]], str]] = []

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_one, pid, season): pid for pid in player_ids}
        for fut in as_completed(futures):
            try:
                results.append(fut.result(timeout=180.0))
            except Exception:
                errors += 1
                sources["fail"] = sources.get("fail", 0) + 1

    seen: Set[int] = set()
    for pid, logs, source in results:
        if pid in seen:
            continue
        seen.add(pid)
        sources[source] = sources.get(source, 0) + 1
        if not logs:
            errors += 1
            continue
        try:
            player_stats_repo.sync_player_game_log_cache(
                db, player_id=pid, season=season, logs=logs
            )
            player_stats_repo.sync_logs_to_player_game_stats(
                db, player_id=pid, season=season, logs=logs, source=source
            )
            db.commit()
            filled += 1
        except Exception:
            db.rollback()
            errors += 1

    return {
        "rows_written": filled,
        "players_targeted": len(player_ids),
        "players_filled": filled,
        "errors": errors,
        "sources": sources,
        "season": season,
    }
