"""Warm player game logs for top players per team."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import player_stats_repo


def _load_existing(pid: int, season: str) -> List[Dict[str, Any]]:
    """Read without hitting external APIs (force_refresh=False)."""
    try:
        logs = NBADataService.fetch_player_game_log(pid, season, force_refresh=False)
        if NBADataService._is_good_game_log(logs):
            return logs or []
    except Exception:
        pass
    return []


def _warm_one(pid: int, season: str, allow_external: bool) -> Tuple[int, bool, str, List[Dict[str, Any]]]:
    """
    Fetch logs for one player (no DB session — thread-safe).
    External refresh is opt-in; cron stays on local cache in offseason.
    """
    existing = _load_existing(pid, season)
    if existing:
        return pid, True, "cache", existing

    if not allow_external:
        return pid, False, "fail", []

    try:
        refreshed = NBADataService.fetch_player_game_log(pid, season, force_refresh=True)
        if NBADataService._is_good_game_log(refreshed):
            return pid, True, "refresh", refreshed or []
    except Exception:
        pass
    return pid, False, "fail", []


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    players_per_team = int(ctx.stats.get("players_per_team", 6))
    # External ESPN/NBA crawl is slow; cron defaults to local cache only.
    allow_external = bool(ctx.stats.get("allow_external", False))

    all_players = NBADataService.fetch_all_players_including_rookies() or []
    players_by_team: Dict[int, List[Dict[str, Any]]] = {}
    for player in all_players:
        team_id = player.get("team_id")
        if not team_id:
            continue
        tid = int(team_id)
        players_by_team.setdefault(tid, [])
        if len(players_by_team[tid]) < players_per_team:
            players_by_team[tid].append(player)

    player_ids = [
        int(p.get("id"))
        for plist in players_by_team.values()
        for p in plist
        if p.get("id")
    ]

    warmed = 0
    errors = 0
    sources: Dict[str, int] = {"cache": 0, "refresh": 0, "fail": 0}
    results: List[Tuple[int, bool, str, List[Dict[str, Any]]]] = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(_warm_one, pid, season, allow_external): pid for pid in player_ids
        }
        for fut in as_completed(futures):
            try:
                results.append(fut.result(timeout=120.0))
            except Exception:
                errors += 1
                sources["fail"] = sources.get("fail", 0) + 1

    # Serial DB writes — shared Session is not thread-safe.
    for pid, ok, source, logs in results:
        sources[source] = sources.get(source, 0) + 1
        if not ok:
            errors += 1
            continue
        try:
            player_stats_repo.sync_player_game_log_cache(
                db, player_id=pid, season=season, logs=logs or []
            )
            player_stats_repo.sync_logs_to_player_game_stats(
                db, player_id=pid, season=season, logs=logs or [], source="nba_api"
            )
            db.commit()
            warmed += 1
        except Exception:
            db.rollback()
            errors += 1
            sources["fail"] = sources.get("fail", 0) + 1

    return {
        "rows_written": warmed,
        "players_targeted": len(player_ids),
        "errors": errors,
        "sources": sources,
        "allow_external": allow_external,
        "season": season,
    }
