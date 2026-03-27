"""
Aggregates live games, rosters, prop lines, trends (L5/L10/L20), and live box stats
for the live prop dashboard.
"""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import structlog

from .espn_api_service import get_espn_service
from .live_game_context_service import LiveGameContextService, get_live_game_context_service
from .espn_mapping_service import get_espn_mapping_service
from .cache_service import get_cache_service
from .live_game_service import LiveGameService
from .nba_api_service import NBADataService
from .over_under_service import LiveGame
from .prop_engine import PropBetEngine
from .stats_calculator import StatsCalculator
from .team_player_service import TeamPlayerService
from ..utils.season import get_current_season

logger = structlog.get_logger()

STAT_KEY = "pts"
PERIODS = (5, 10, 20)
PERIOD_LABELS = {5: "L5", 10: "L10", 20: "L20"}


def _mock_american_odds(seed: str) -> Tuple[str, str]:
    """Deterministic placeholder odds until sportsbook integration exists."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    over_v = -115 - (h % 21)
    under_v = -105 + (h % 31)
    if over_v >= -100:
        over_v = -110
    if under_v >= -100:
        under_v = -108
    return (str(over_v), f"+{105 + (h % 40)}")


def _resolve_teams_for_game(game_id: str) -> Tuple[Optional[str], Optional[str]]:
    live_svc = LiveGameService()
    game = live_svc.get_game_by_id(game_id)
    if game:
        return game.home_team, game.away_team
    try:
        espn = get_espn_service()
        summary = espn.get_game_summary(game_id)
        if summary:
            competitions = summary.get("header", {}).get("competitions", [])
            if competitions:
                comp = competitions[0]
                home_abbr = None
                away_abbr = None
                for competitor in comp.get("competitors", []):
                    team_data = competitor.get("team", {})
                    abbr = team_data.get("abbreviation", "")
                    if competitor.get("homeAway") == "home":
                        home_abbr = abbr
                    else:
                        away_abbr = abbr
                return home_abbr, away_abbr
    except Exception as e:
        logger.warning("resolve_teams espn failed", game_id=game_id, error=str(e))
    return None, None


def _team_ids_from_abbr(home_abbr: str, away_abbr: str) -> Tuple[Optional[int], Optional[int]]:
    teams = NBADataService.fetch_all_teams()
    home = next((t for t in teams if t.get("abbreviation") == home_abbr), None)
    away = next((t for t in teams if t.get("abbreviation") == away_abbr), None)
    if not home or not away:
        return None, None
    return home.get("id"), away.get("id")


def _game_to_summary(g: LiveGame) -> Dict[str, Any]:
    is_live = (not g.is_final) and (g.quarter or 0) > 0
    return {
        "game_id": g.game_id,
        "home_team": g.home_team,
        "away_team": g.away_team,
        "home_score": g.home_score,
        "away_score": g.away_score,
        "quarter": g.quarter,
        "time_remaining": g.time_remaining,
        "is_final": g.is_final,
        "is_live": is_live,
        "current_total": g.home_score + g.away_score,
    }


def _empty_trend_block() -> Dict[str, Any]:
    return {
        PERIOD_LABELS[n]: {
            "hit_rate_percentage": 0,
            "hits": 0,
            "total": 0,
            "results": [],
        }
        for n in PERIODS
    }


def _live_box_stats(
    game: LiveGame, player_id: int, nba_live: Dict[int, Dict[str, Any]]
) -> Tuple[float, float, float, float]:
    pstats = nba_live.get(int(player_id), {})
    pts = float(pstats.get("pts", 0) or 0)
    reb = float(pstats.get("reb", 0) or 0)
    ast = float(pstats.get("ast", 0) or 0)
    minutes_played = float(pstats.get("minutes", 0) or 0)
    if (game.quarter or 0) == 0 or game.is_final:
        return 0.0, 0.0, 0.0, 0.0
    return pts, reb, ast, minutes_played


def _process_player(
    game: LiveGame,
    player: Dict[str, Any],
    team_abbr: str,
    season: str,
    game_live_pace: float,
    nba_live: Dict[int, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    player_id = player.get("id")
    if not player_id:
        return None
    try:
        pid_int = int(player_id)
    except (TypeError, ValueError):
        return None

    try:
        logs = NBADataService.fetch_player_game_log(pid_int, season)
    except Exception:
        logs = []

    pts, reb, ast, minutes_played = _live_box_stats(game, pid_int, nba_live)
    name = player.get("name") or f"Player {player_id}"
    pos = (player.get("position") or "").strip() or "—"
    headshot_url = f"https://cdn.nba.com/headshots/nba/latest/260x190/{pid_int}.png"

    # Roster-only / no game log: still return a row so every roster player appears.
    if not logs:
        line = max(0.5, round(pts * 2) / 2.0) if pts > 0 else 8.0
        prog = LiveGameContextService.compute_stat_progression(
            pts, line, minutes_played, live_pace=game_live_pace
        )
        over_odds, under_odds = _mock_american_odds(f"{pid_int}:{line}:{STAT_KEY}:nodata")
        prop_row = {
            "prop_type": "points",
            "stat_key": STAT_KEY,
            "line": line,
            "suggestion": "over",
            "confidence": 0.0,
            "odds_over": over_odds,
            "odds_under": under_odds,
            "progression": prog,
            "trend": _empty_trend_block(),
            "rationale_summary": "No NBA game log for this season yet — roster listing only; trends unavailable.",
        }
        return {
            "player_id": pid_int,
            "name": name,
            "team": team_abbr,
            "position": pos,
            "rotation_tier": False,
            "headshot_url": headshot_url,
            "live_stats": {"pts": int(pts), "reb": int(reb), "ast": int(ast)},
            "props": [prop_row],
        }

    minutes_list = [float(g.get("minutes", 0) or 0) for g in logs if g.get("minutes")]
    avg_min = sum(minutes_list) / len(minutes_list) if minutes_list else 0.0
    rotation_tier = avg_min >= 22.0

    for g in logs:
        g["pra"] = float(g.get("pts", 0) or 0) + float(g.get("reb", 0) or 0) + float(g.get("ast", 0) or 0)

    line = PropBetEngine.determine_line_value(logs, STAT_KEY)
    ev = PropBetEngine.evaluate_prop(logs, STAT_KEY, line)
    direction = (ev.get("suggestion") or "over").lower()
    if direction not in ("over", "under"):
        direction = "over"

    trend: Dict[str, Any] = {}
    for n in PERIODS:
        label = PERIOD_LABELS[n]
        trend[label] = StatsCalculator.trend_period(logs, line, STAT_KEY, direction, n)

    prog = LiveGameContextService.compute_stat_progression(
        pts, line, minutes_played, live_pace=game_live_pace
    )
    over_odds, under_odds = _mock_american_odds(f"{pid_int}:{line}:{STAT_KEY}")

    prop_row = {
        "prop_type": "points",
        "stat_key": STAT_KEY,
        "line": line,
        "suggestion": direction,
        "confidence": ev.get("confidence", 0),
        "odds_over": over_odds,
        "odds_under": under_odds,
        "progression": prog,
        "trend": trend,
        "rationale_summary": (ev.get("rationale") or {}).get("summary", ""),
    }

    return {
        "player_id": pid_int,
        "name": name,
        "team": team_abbr,
        "position": pos,
        "rotation_tier": rotation_tier,
        "headshot_url": headshot_url,
        "live_stats": {"pts": int(pts), "reb": int(reb), "ast": int(ast)},
        "props": [prop_row],
    }


def _build_nba_live_lookup(
    espn_game_id: str,
    roster_player_ids: List[int],
    include_live_box: bool,
) -> tuple[float, Dict[int, Dict[str, Any]]]:
    if not include_live_box:
        return 0.0, {}
    ctx_svc = get_live_game_context_service()
    pace, by_espn = ctx_svc.get_batch_live_box_for_game(espn_game_id)
    mapping = get_espn_mapping_service()
    nba_live: Dict[int, Dict[str, Any]] = {}
    for pid in roster_player_ids:
        try:
            eid = mapping.get_espn_player_id(int(pid))
        except Exception:
            continue
        if not eid:
            continue
        row = by_espn.get(str(eid))
        if row:
            nba_live[int(pid)] = row
    return pace, nba_live


def get_live_props_dashboard(
    game_id: Optional[str] = None,
    season: Optional[str] = None,
    max_workers: int = 10,
    include_live_box: bool = True,
    use_response_cache: bool = True,
) -> Dict[str, Any]:
    season_use = season or get_current_season()
    live_svc = LiveGameService()
    all_games = live_svc.get_todays_games()
    summaries = [_game_to_summary(g) for g in all_games]

    target_game: Optional[LiveGame] = None
    if game_id:
        for g in all_games:
            if g.game_id == game_id:
                target_game = g
                break
        if not target_game:
            return {
                "games": summaries,
                "selected_game_id": None,
                "players": [],
                "confidence": [],
                "market_sentiment": None,
                "error": "Game not found in today's slate",
            }
    else:
        for g in all_games:
            if not g.is_final:
                target_game = g
                break
        if not target_game and all_games:
            target_game = all_games[0]

    if not target_game:
        return {
            "games": summaries,
            "selected_game_id": None,
            "players": [],
            "confidence": [],
            "market_sentiment": None,
        }

    cache = get_cache_service()
    cache_key = f"live_props_dash:v4:{target_game.game_id}:{season_use}:{int(include_live_box)}"
    if use_response_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    home_abbr = target_game.home_team or ""
    away_abbr = target_game.away_team or ""
    if not home_abbr or not away_abbr:
        rh, ra = _resolve_teams_for_game(target_game.game_id)
        home_abbr = home_abbr or rh or ""
        away_abbr = away_abbr or ra or ""

    hid, aid = _team_ids_from_abbr(home_abbr, away_abbr)
    if not hid or not aid:
        return {
            "games": summaries,
            "selected_game_id": target_game.game_id,
            "players": [],
            "confidence": [],
            "market_sentiment": None,
            "error": "Could not resolve team IDs",
        }

    home_players = TeamPlayerService.get_players_for_team(hid)
    away_players = TeamPlayerService.get_players_for_team(aid)

    tasks: List[Tuple[LiveGame, Dict[str, Any], str]] = []
    for p in home_players:
        tasks.append((target_game, p, home_abbr))
    for p in away_players:
        tasks.append((target_game, p, away_abbr))

    roster_ids: List[int] = []
    for _, pl, _ in tasks:
        pid = pl.get("id")
        if pid is not None:
            try:
                roster_ids.append(int(pid))
            except (TypeError, ValueError):
                pass

    game_live_pace, nba_live = _build_nba_live_lookup(
        target_game.game_id, roster_ids, include_live_box
    )

    players_out: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [
            ex.submit(_process_player, g, pl, ab, season_use, game_live_pace, nba_live)
            for g, pl, ab in tasks
        ]
        for fut in as_completed(futs):
            try:
                row = fut.result()
                if row:
                    players_out.append(row)
            except Exception as e:
                logger.debug("live_props player skip", error=str(e))

    players_out.sort(key=lambda r: r.get("props", [{}])[0].get("confidence", 0), reverse=True)

    confidence_cards: List[Dict[str, Any]] = []
    for r in players_out[:12]:
        prop0 = r["props"][0]
        conf = float(prop0.get("confidence") or 0)
        direction = prop0.get("suggestion", "over")
        line = prop0.get("line", 0)
        label = f"{r['name']} {direction.title()} {line}"
        tier = "lock" if conf >= 72 else ("risk" if conf < 38 else "neutral")
        confidence_cards.append(
            {
                "tier": tier,
                "label": label,
                "confidence_pct": int(round(conf)),
                "player_id": r["player_id"],
                "rationale": prop0.get("rationale_summary", ""),
                "trend_L5_hit": prop0.get("trend", {}).get("L5", {}).get("hit_rate_percentage", 0),
            }
        )

    hs = target_game.home_score
    as_ = target_game.away_score
    diff = hs - as_
    leader = target_game.home_team if diff >= 0 else target_game.away_team
    bars = [40, 55, 70, 85, 45, 25]
    if diff != 0:
        bars = [min(100, 35 + abs(diff) * 3 + i * 8) for i in range(6)]

    result: Dict[str, Any] = {
        "games": summaries,
        "selected_game_id": target_game.game_id,
        "home_team": home_abbr,
        "away_team": away_abbr,
        "players": players_out,
        "confidence": confidence_cards[:6],
        "market_sentiment": {
            "bars": bars,
            "headline_team": leader,
            "spread_note": f"{leader} side — model blend (placeholder)",
        },
        "live_box_applied": include_live_box,
    }
    if use_response_cache and not result.get("error"):
        cache.set(cache_key, result, ttl=25)
    return result
