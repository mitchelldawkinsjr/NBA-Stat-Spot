"""
ESPN-based player game log fallback.
Builds game log from ESPN game summary box scores when nba_api is flaky or empty.
Uses: team schedule -> game summary (box score) per game -> find player stats.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger()

# Stat keys in ESPN boxscore statistics[0].keys (order matches stats array)
ESPN_STAT_KEYS = [
    "minutes", "points", "fieldGoalsMade-fieldGoalsAttempted",
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
    "freeThrowsMade-freeThrowsAttempted", "rebounds", "assists",
    "turnovers", "steals", "blocks", "offensiveRebounds", "defensiveRebounds",
    "fouls", "plusMinus",
]


def _parse_minutes(min_val: Any) -> float:
    """Parse minutes from ESPN (string like '28' or '34:30')."""
    if min_val is None or min_val == "":
        return 0.0
    s = str(min_val).strip()
    if not s:
        return 0.0
    if ":" in s:
        parts = s.split(":")
        if len(parts) >= 2:
            try:
                return float(parts[0]) + (float(parts[1]) / 60.0)
            except (ValueError, TypeError):
                pass
        try:
            return float(parts[0])
        except (ValueError, TypeError, IndexError):
            return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _parse_three_from_fg_string(fg_str: str) -> int:
    """Parse 3PM from FG string like '4-12' (first number) or from 3PT string '3-6'."""
    if not fg_str or not isinstance(fg_str, str):
        return 0
    parts = fg_str.split("-")
    if len(parts) >= 1:
        try:
            return int(parts[0].strip())
        except (ValueError, TypeError):
            pass
    return 0


def fetch_player_game_log_espn(
    player_id: int,
    season: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """
    Build player game log from ESPN game summaries (box scores).
    Call when nba_api returns empty or fails. Uses NBA player_id; resolves to ESPN ID via roster.

    Returns:
        List of game log dicts: game_id, game_date, matchup, pts, reb, ast, tpm, minutes
    """
    try:
        from .espn_api_service import get_espn_service
        from .espn_mapping_service import ESPNMappingService
        from .nba_api_service import NBADataService
    except ImportError as e:
        logger.warning("ESPN game log fallback unavailable", error=str(e))
        return []

    espn = get_espn_service()
    mapping = ESPNMappingService()

    # Get player name and team from our roster (nba_api roster)
    players = NBADataService.fetch_all_players_including_rookies() or []
    player = next((p for p in players if p.get("id") is not None and int(p.get("id")) == int(player_id)), None)
    if not player:
        logger.info("ESPN fallback: player not in roster", player_id=player_id)
        return []

    player_name = player.get("full_name") or (player.get("first_name", "") + " " + player.get("last_name", "")).strip()
    team_id = player.get("team_id")
    if not player_name or team_id is None:
        logger.info("ESPN fallback: missing name or team", player_id=player_id)
        return []

    espn_player_id = mapping.match_player_by_name(player_name, int(team_id))
    if not espn_player_id:
        logger.info("ESPN fallback: could not map to ESPN player", player_id=player_id, name=player_name)
        return []

    espn_slug = mapping.get_espn_team_slug(int(team_id))
    if not espn_slug:
        logger.info("ESPN fallback: no ESPN team slug", player_id=player_id, team_id=team_id)
        return []

    # Get team schedule (events = games); sort by date descending (most recent first)
    events = espn.get_team_schedule(espn_slug)
    if not events:
        logger.info("ESPN fallback: no schedule", player_id=player_id, espn_slug=espn_slug)
        return []

    def _event_date(e: Dict[str, Any]) -> str:
        d = e.get("date") or (e.get("competitions") or [{}])[0].get("date") if e.get("competitions") else ""
        return (d[:10] if d else "") or "0000-00-00"

    # Pre-filter to completed games only, then sort most recent first
    completed_events = []
    for ev in events:
        comp = (ev.get("competitions") or [{}])[0] if ev.get("competitions") else {}
        st_obj = comp.get("status") or ev.get("status") or {}
        st_type = st_obj.get("type", {}) if isinstance(st_obj, dict) else {}
        st_state = st_type.get("state", "") if isinstance(st_type, dict) else ""
        if st_state == "post" or "post" in st_state.lower():
            completed_events.append(ev)
    events_sorted = sorted(completed_events, key=_event_date, reverse=True)

    log_entries: List[Dict[str, Any]] = []
    seen_game_ids: set = set()

    for event in events_sorted[: limit + 10]:
        if len(log_entries) >= limit:
            break
        event_id = event.get("id")
        if not event_id or event_id in seen_game_ids:
            continue
        summary = espn.get_game_summary(str(event_id))
        if not summary:
            continue
        box = summary.get("boxscore") or {}
        teams = box.get("teams") or []
        header = summary.get("header") or {}
        comps = header.get("competitions") or []
        comp = comps[0] if comps else {}
        comp_date = comp.get("date", "")[:10] if comp.get("date") else ""
        competitors = comp.get("competitors") or []
        home_away = {}
        for c in competitors:
            ha = (c.get("homeAway") or "").lower()
            abbr = (c.get("team") or {}).get("abbreviation") or ""
            if abbr:
                home_away[ha] = abbr

        # Player-level box scores are in boxscore.players[], not boxscore.teams[]
        player_blocks = box.get("players") or []
        for player_block in player_blocks:
            stats_blocks = player_block.get("statistics") or []
            team_info = player_block.get("team") or {}
            team_abbr = team_info.get("abbreviation") or ""
            ha = (player_block.get("displayOrder") or 0)
            # Determine home/away from the teams list
            team_ha = ""
            for tb in teams:
                if (tb.get("team") or {}).get("abbreviation") == team_abbr:
                    team_ha = (tb.get("homeAway") or "").lower()
                    break
            for stat_block in stats_blocks:
                athletes = stat_block.get("athletes") or []
                keys = stat_block.get("keys") or ESPN_STAT_KEYS
                for ath in athletes:
                    a = ath.get("athlete") or {}
                    if str(a.get("id")) != str(espn_player_id):
                        continue
                    seen_game_ids.add(event_id)
                    raw_stats = ath.get("stats") or []
                    stat_map = {}
                    for i, k in enumerate(keys):
                        if i < len(raw_stats):
                            stat_map[k] = raw_stats[i]

                    pts = 0
                    if "points" in stat_map and stat_map["points"] not in (None, ""):
                        try:
                            pts = int(stat_map["points"])
                        except (ValueError, TypeError):
                            pass
                    reb = 0
                    if "rebounds" in stat_map and stat_map["rebounds"] not in (None, ""):
                        try:
                            reb = int(stat_map["rebounds"])
                        except (ValueError, TypeError):
                            pass
                    ast = 0
                    if "assists" in stat_map and stat_map["assists"] not in (None, ""):
                        try:
                            ast = int(stat_map["assists"])
                        except (ValueError, TypeError):
                            pass
                    tpm = 0
                    three_key = "threePointFieldGoalsMade-threePointFieldGoalsAttempted"
                    if three_key in stat_map and stat_map[three_key]:
                        tpm = _parse_three_from_fg_string(str(stat_map[three_key]))
                    minutes = _parse_minutes(stat_map.get("minutes"))

                    def _safe_int(v: Any) -> int:
                        if v is None or v == "":
                            return 0
                        try:
                            return int(v)
                        except (ValueError, TypeError):
                            return 0

                    fg_key = "fieldGoalsMade-fieldGoalsAttempted"
                    ft_key = "freeThrowsMade-freeThrowsAttempted"
                    fg_str = str(stat_map.get(fg_key) or "0-0")
                    ft_str = str(stat_map.get(ft_key) or "0-0")
                    fg_parts = fg_str.split("-")
                    ft_parts = ft_str.split("-")
                    try:
                        fga = int(fg_parts[1])
                    except (ValueError, TypeError, IndexError):
                        fga = 0
                    try:
                        fta = int(ft_parts[1])
                    except (ValueError, TypeError, IndexError):
                        fta = 0
                    tov = _safe_int(stat_map.get("turnovers"))
                    oreb = _safe_int(stat_map.get("offensiveRebounds"))
                    stl = _safe_int(stat_map.get("steals"))
                    blk = _safe_int(stat_map.get("blocks"))

                    opp_abbr = home_away.get("away") if team_ha == "home" else home_away.get("home")
                    matchup = f"{team_abbr} vs. {opp_abbr}" if team_ha == "home" else f"{team_abbr} @ {opp_abbr}"
                    if not opp_abbr:
                        matchup = team_abbr

                    log_entries.append({
                        "game_id": str(event_id),
                        "game_date": comp_date or datetime.utcnow().date().isoformat(),
                        "matchup": matchup,
                        "pts": pts,
                        "reb": reb,
                        "ast": ast,
                        "tpm": tpm,
                        "minutes": minutes,
                        "fga": fga,
                        "fta": fta,
                        "tov": tov,
                        "oreb": oreb,
                        "stl": stl,
                        "blk": blk,
                    })
                    break
                if len(log_entries) and log_entries[-1].get("game_id") == str(event_id):
                    break

    # Sort by date descending (most recent first)
    log_entries.sort(key=lambda x: x.get("game_date") or "", reverse=True)
    result = log_entries[:limit]
    if result:
        logger.info("ESPN game log fallback returned entries", player_id=player_id, count=len(result))
    return result


