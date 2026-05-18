"""Warm player game logs for top players per team."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import player_stats_repo


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    players_per_team = int(ctx.stats.get("players_per_team", 6))

    teams = NBADataService.fetch_all_teams() or []
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

    def _fetch(pid: int) -> bool:
        try:
            logs = NBADataService.fetch_player_game_log(pid, season, force_refresh=True)
            return bool(logs)
        except Exception:
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch, pid): pid for pid in player_ids}
        for fut in as_completed(futures):
            pid = futures[fut]
            try:
                ok = fut.result(timeout=90.0)
                if ok:
                    logs = NBADataService.fetch_player_game_log(pid, season, force_refresh=False)
                    player_stats_repo.sync_player_game_log_cache(
                        db, player_id=pid, season=season, logs=logs or []
                    )
                    warmed += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

    return {
        "rows_written": warmed,
        "players_targeted": len(player_ids),
        "errors": errors,
        "season": season,
    }
