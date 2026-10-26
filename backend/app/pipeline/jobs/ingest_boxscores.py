"""Ingest box scores for FINAL games into player_game_stats."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from ...services.espn_api_service import get_espn_service
from ...services.espn_game_log import _parse_minutes
from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import games_repo, player_stats_repo
from ..utils.player_match import build_name_team_index, match_espn_athlete


def _safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


def _parse_boxscore_players(
    summary: Dict[str, Any],
    player_index: Dict,
) -> List[Dict[str, Any]]:
    """Extract per-player stats from ESPN summary with NBA player_id."""
    out: List[Dict[str, Any]] = []
    box = summary.get("boxscore") or {}
    players_blocks = box.get("players") or []
    teams_meta = box.get("teams") or []

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

                tpm = 0
                three_key = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
                if stat_map.get(three_key):
                    tpm = _safe_int(str(stat_map[three_key]).split("-")[0])

                nba_id = match_espn_athlete(a, team_abbr, player_index)
                if not nba_id:
                    continue
                out.append(
                    {
                        "player_id": nba_id,
                        "team_abbr": team_abbr,
                        "pts": _safe_int(stat_map.get("points")),
                        "reb": _safe_int(stat_map.get("rebounds")),
                        "ast": _safe_int(stat_map.get("assists")),
                        "tpm": tpm,
                        "minutes": _parse_minutes(stat_map.get("minutes")),
                        "stl": _safe_int(stat_map.get("steals")),
                        "blk": _safe_int(stat_map.get("blocks")),
                        "tov": _safe_int(stat_map.get("turnovers")),
                    }
                )
    return out


def log_cache_row(
    p: Dict[str, Any], *, game_id: str, game_date: date, home_abbr: str, away_abbr: str
) -> Dict[str, Any]:
    """Shape a parsed box-score player as a game-log row (team-perspective matchup)."""
    team = p.get("team_abbr") or ""
    if team and team == home_abbr:
        matchup = f"{team} vs. {away_abbr}"
    elif team and team == away_abbr:
        matchup = f"{team} @ {home_abbr}"
    else:
        matchup = f"{away_abbr} @ {home_abbr}" if away_abbr and home_abbr else ""
    return {
        "game_id": game_id,
        "game_date": game_date.isoformat(),
        "matchup": matchup,
        "pts": p["pts"],
        "reb": p["reb"],
        "ast": p["ast"],
        "tpm": p["tpm"],
        "minutes": p["minutes"],
        "stl": p["stl"],
        "blk": p["blk"],
        "tov": p["tov"],
    }


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    today = ctx.target_date or date.today()
    from_d = ctx.from_date or (today - timedelta(days=1))
    to_d = ctx.to_date or today

    games = games_repo.list_games_for_dates(db, from_d, to_d, status="FINAL")

    all_players = NBADataService.fetch_all_players_including_rookies() or []
    player_index = build_name_team_index(all_players)
    espn = get_espn_service()

    stats_written = 0
    participants: Set[int] = set()
    errors = 0

    for game in games:
        summary = espn.get_game_summary(str(game.game_id))
        if not summary:
            errors += 1
            continue

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

            try:
                player_stats_repo.merge_game_into_log_cache(
                    db,
                    player_id=pid,
                    season=season,
                    row=log_cache_row(
                        p,
                        game_id=game.game_id,
                        game_date=gdate,
                        home_abbr=game.home_team_abbr or "",
                        away_abbr=game.away_team_abbr or "",
                    ),
                )
            except Exception:
                errors += 1

    db.commit()
    for pid in participants:
        NBADataService.invalidate_player_game_log(pid, season)

    return {
        "rows_written": stats_written,
        "games_processed": len(games),
        "participants": len(participants),
        "errors": errors,
        "last_game_date": to_d.isoformat(),
    }
