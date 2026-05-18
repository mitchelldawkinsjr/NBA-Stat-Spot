"""Ingest box scores for FINAL games into player_game_stats."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from ...services.espn_api_service import get_espn_service
from ...services.live_game_context_service import _build_espn_box_index_from_summary
from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import games_repo, player_stats_repo
from ..utils.player_match import build_name_team_index, match_espn_athlete


def _parse_boxscore_players(
    summary: Dict[str, Any],
    player_index: Dict,
) -> List[Dict[str, Any]]:
    """Extract per-player stats from ESPN summary with NBA player_id."""
    out: List[Dict[str, Any]] = []
    box = summary.get("boxscore") or {}
    players_blocks = box.get("players") or []
    teams_meta = box.get("teams") or []

    team_abbr_by_ha: Dict[str, str] = {}
    for tb in teams_meta:
        ha = (tb.get("homeAway") or "").lower()
        abbr = ((tb.get("team") or {}).get("abbreviation") or "").upper()
        if ha and abbr:
            team_abbr_by_ha[ha] = abbr

    for player_block in players_blocks:
        team_info = player_block.get("team") or {}
        team_abbr = (team_info.get("abbreviation") or "").upper()
        if not team_abbr:
            for tb in teams_meta:
                if (tb.get("team") or {}).get("id") == team_info.get("id"):
                    team_abbr = ((tb.get("team") or {}).get("abbreviation") or "").upper()
                    break

        for stat_block in player_block.get("statistics") or []:
            keys = stat_block.get("keys") or []
            for ath in stat_block.get("athletes") or []:
                a = ath.get("athlete") or {}
                raw_stats = ath.get("stats") or []
                stat_map: Dict[str, Any] = {}
                for i, k in enumerate(keys):
                    if i < len(raw_stats):
                        stat_map[k] = raw_stats[i]

                pts = reb = ast = tpm = 0
                try:
                    pts = int(stat_map.get("points") or 0)
                except (ValueError, TypeError):
                    pass
                try:
                    reb = int(stat_map.get("rebounds") or 0)
                except (ValueError, TypeError):
                    pass
                try:
                    ast = int(stat_map.get("assists") or 0)
                except (ValueError, TypeError):
                    pass
                three_key = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
                if three_key in stat_map and stat_map[three_key]:
                    parts = str(stat_map[three_key]).split("-")
                    if parts:
                        try:
                            tpm = int(parts[0])
                        except ValueError:
                            pass

                from ...services.espn_game_log import _parse_minutes

                minutes = _parse_minutes(stat_map.get("minutes"))
                nba_id = match_espn_athlete(a, team_abbr, player_index)
                if not nba_id:
                    continue
                out.append(
                    {
                        "player_id": nba_id,
                        "pts": pts,
                        "reb": reb,
                        "ast": ast,
                        "tpm": tpm,
                        "minutes": minutes,
                        "stl": 0,
                        "blk": 0,
                        "tov": 0,
                    }
                )
    return out


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    today = ctx.target_date or date.today()
    from_d = ctx.from_date or (today - timedelta(days=1))
    to_d = ctx.to_date or today

    games = games_repo.list_games_for_dates(db, from_d, to_d, status="FINAL")
    if not games:
        games = games_repo.list_games_for_dates(db, from_d, to_d)

    all_players = NBADataService.fetch_all_players_including_rookies() or []
    player_index = build_name_team_index(all_players)
    espn = get_espn_service()

    stats_written = 0
    participants: Set[int] = set()
    errors = 0

    for game in games:
        if game.status != "FINAL":
            continue
        espn_id = game.game_id
        summary = espn.get_game_summary(str(espn_id))
        if not summary:
            errors += 1
            continue

        players = _parse_boxscore_players(summary, player_index)
        if not players:
            idx = _build_espn_box_index_from_summary(summary)
            for espn_aid, st in idx.items():
                pass
            players = _parse_boxscore_players(summary, player_index)

        gdate = game.game_date
        for p in players:
            pid = p["player_id"]
            try:
                player_stats_repo.upsert_player_game_stat(
                    db,
                    player_id=pid,
                    game_id=game.game_id,
                    game_date=gdate,
                    season=season,
                    stats=p,
                    source="espn",
                )
                player_stats_repo.record_game_participant(db, game.game_id, pid)
                participants.add(pid)
                stats_written += 1
            except Exception:
                errors += 1
                continue

        log_rows = []
        for p in players:
            log_rows.append(
                {
                    "game_id": game.game_id,
                    "game_date": gdate.isoformat(),
                    "matchup": f"{game.away_team_abbr} @ {game.home_team_abbr}",
                    "pts": p["pts"],
                    "reb": p["reb"],
                    "ast": p["ast"],
                    "tpm": p["tpm"],
                    "minutes": p["minutes"],
                }
            )
        for pid in {p["player_id"] for p in players}:
            plogs = [
                r
                for r in log_rows
            ]
            try:
                existing = NBADataService.fetch_player_game_log(pid, season, force_refresh=False)
                merged = {str(x.get("game_id")): x for x in (existing or [])}
                for r in plogs:
                    merged[str(r["game_id"])] = r
                player_stats_repo.sync_player_game_log_cache(
                    db, player_id=pid, season=season, logs=list(merged.values())
                )
            except Exception:
                pass

    return {
        "rows_written": stats_written,
        "games_processed": len(games),
        "participants": len(participants),
        "errors": errors,
        "last_game_date": to_d.isoformat(),
    }
