"""
Best Picks Service — unified "Top Picks of the Day" for the homepage.

Pipeline:
  1. Find every player playing today.
  2. For each player × stat, generate a realistic sportsbook-style line using
     season average, recent form (5–10 games), and opponent defensive strength.
  3. Evaluate over/under vs that line; score with multi-factor confidence.
  4. Output: player, stat category, generated line, prediction (Over/Under), confidence.
  5. Tiers: Lock / Strong / Lean.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _game_date_sort_key(g: Dict) -> Any:
    """Return a sort key for game_date (newest first). Handles YYYY-MM-DD and API formats like 'FEB 15, 2025'."""
    gd = g.get("game_date") or ""
    if not gd:
        return ""
    # YYYY-MM-DD
    if len(gd) >= 10 and gd[4] == "-" and gd[7] == "-":
        return gd
    try:
        # e.g. "FEB 15, 2025" or "Feb 15, 2025"
        dt = datetime.strptime(gd.strip(), "%b %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    try:
        dt = datetime.strptime(gd.strip(), "%B %d, %Y")  # "February 15, 2025"
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    return gd

from .insight_scoring import compute_matchup_score
from .nba_api_service import NBADataService
from .prop_engine import PropBetEngine
from .stats_calculator import StatsCalculator


STAT_TYPES = ["pts", "reb", "ast", "tpm"]
DISPLAY = {"pts": "PTS", "reb": "REB", "ast": "AST", "tpm": "3PM", "pra": "PRA"}
# Pick type (PTS, REB, ...) -> stat key for insight_scoring
TYPE_TO_STAT = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm", "PRA": "pra"}
# Map stat to defensive rank key (opponent def rank 1 = best defense)
DEF_RANK_KEY = {"pts": "pts", "reb": "reb", "ast": "ast", "tpm": "3pm", "pra": "pts"}

TIER_LOCK = 78
TIER_STRONG = 62
TIER_LEAN = 45


def _tier_label(confidence: float) -> str:
    if confidence >= TIER_LOCK:
        return "lock"
    if confidence >= TIER_STRONG:
        return "strong"
    return "lean"


def _enrich_pra(logs: List[Dict]) -> List[Dict]:
    for g in logs:
        g["pra"] = (
            float(g.get("pts", 0) or 0)
            + float(g.get("reb", 0) or 0)
            + float(g.get("ast", 0) or 0)
        )
    return logs


def _avg_minutes(logs: List[Dict]) -> float:
    mins = [
        float(g.get("minutes", 0) or 0)
        for g in logs
        if g.get("minutes") and float(g.get("minutes", 0) or 0) > 0
    ]
    return sum(mins) / len(mins) if mins else 0.0


def _normalize_position(raw_pos: Optional[str]) -> Optional[str]:
    """Normalize player position to PG, SG, SF, PF, or C for position-defense lookup."""
    if not raw_pos:
        return None
    r = (raw_pos or "").upper().strip()
    if r in ("G", "PG", "GUARD"):
        return "PG"
    if r in ("SG", "SHOOTING GUARD"):
        return "SG"
    if r in ("SF", "SMALL FORWARD", "F", "FORWARD", "G-F", "F-G"):
        return "SF"
    if r in ("PF", "POWER FORWARD", "F-C", "C-F"):
        return "PF"
    if r in ("C", "CENTER"):
        return "C"
    return None


def _blend_def_rank(team_rank: Optional[int], pos_rank: Optional[int]) -> int:
    """Blend team-level and position-level defensive rank; higher rank number = worse defense."""
    if team_rank is None and pos_rank is None:
        return 15
    if pos_rank is None:
        return team_rank if team_rank is not None else 15
    if team_rank is None:
        return pos_rank
    return round(0.6 * team_rank + 0.4 * pos_rank)


def _generate_sportsbook_line(
    logs: List[Dict],
    stat: str,
    n_recent: int = 10,
    opponent_def_rank: Optional[int] = None,
    opponent_pos_def_rank: Optional[int] = None,
) -> float:
    """
    Generate a realistic prop line (sportsbook-style) using:
    - Player season/rolling average as baseline
    - Recent form (last 5–10 games) adjustment
    - Opponent defensive strength (team + position rank; 1 = best D → slightly lower line)
    Returns half-point line (e.g. 24.5, 7.0).
    """
    if not logs:
        return 0.0
    # Caller passes logs sorted newest-first; use first n for "most recent"
    n_baseline = min(10, len(logs))
    baseline = StatsCalculator.calculate_rolling_average(logs[:n_baseline], stat, n_games=n_baseline)
    recent_n = min(5, len(logs))
    recent_avg = StatsCalculator.calculate_rolling_average(logs[:recent_n], stat, n_games=recent_n)
    form_adj = (recent_avg - baseline) * 0.35
    rank = _blend_def_rank(opponent_def_rank, opponent_pos_def_rank)
    matchup_adj = (rank - 15) / 20.0
    raw = baseline + form_adj + matchup_adj
    line = round(raw * 2) / 2.0
    if stat == "tpm":
        line = max(0.0, line)
    else:
        line = max(0.5, line)
    return line


def _opp_def_score(rank: Optional[int]) -> float:
    """Convert opponent def rank (1=best) to 0–1 score for confidence (higher = easier matchup)."""
    if rank is None:
        return 0.5
    return max(0.0, min(1.0, (31 - rank) / 30.0))


def _scan_player(
    player_id: int,
    player_name: str,
    season: str,
    target_date: str,
    n_recent: int = 10,
    opponent_def_ranks: Optional[Dict[str, int]] = None,
    opponent_pos_def_ranks: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Return one pick per stat: realistic line (sportsbook-style), then over/under prediction and confidence."""
    try:
        logs = NBADataService.fetch_player_game_log(player_id, season)
        if not logs or len(logs) < 3:
            return [], []
        if _avg_minutes(logs) < 18.0:
            return [], []
        logs = _enrich_pra(logs)
        # Sort by game_date descending so "recent" = most recent games (API order is not guaranteed)
        logs = sorted(logs, key=_game_date_sort_key, reverse=True)
    except Exception:
        return [], []

    ranks = opponent_def_ranks or {}
    pos_ranks = opponent_pos_def_ranks or {}
    all_stats = STAT_TYPES + ["pra"]
    results: List[Dict[str, Any]] = []
    min_games = 5

    for stat in all_stats:
        try:
            if len(logs) < min_games:
                continue
            rk_key = DEF_RANK_KEY.get(stat, "pts")
            opp_rank = ranks.get(rk_key)
            opp_pos_rank = pos_ranks.get(rk_key)
            line = _generate_sportsbook_line(
                logs, stat, n_recent,
                opponent_def_rank=opp_rank,
                opponent_pos_def_rank=opp_pos_rank,
            )
            # Use the most recent n_recent games by date (logs are sorted newest first)
            recent = logs[:n_recent] if n_recent else logs
            hr_over = StatsCalculator.calculate_hit_rate(recent, line, stat, "over")
            hr_under = StatsCalculator.calculate_hit_rate(recent, line, stat, "under")
            direction = "over" if hr_over >= hr_under else "under"
            hr = hr_over if direction == "over" else hr_under

            blended_rank = _blend_def_rank(opp_rank, opp_pos_rank)
            opp_score = _opp_def_score(blended_rank)
            confidence = PropBetEngine.multi_factor_confidence(
                logs, stat, line, direction, opp_def_score=opp_score
            )
            # Form/consistency over most recent games (logs are newest-first)
            form = StatsCalculator.calculate_recent_form(recent, stat, n_games=min(5, len(recent)))
            consistency = StatsCalculator.calculate_consistency(recent, stat, n_games=len(recent))
            # Streak expects chronological order (most recent last); recent is newest-first so reverse
            streak = StatsCalculator.calculate_streak(
                list(reversed(recent)), stat, line, direction
            )

            rationale = PropBetEngine.build_rationale_text(
                hr, direction, line, form["trend"], consistency, streak, min(len(logs), n_recent)
            )

            key = DISPLAY.get(stat, stat.upper())
            results.append(
                {
                    "type": key,
                    "playerId": player_id,
                    "playerName": player_name,
                    "marketLine": line,
                    "fairLine": line,
                    "confidence": confidence,
                    "suggestion": direction,
                    "hitRate": round(hr * 100, 1),
                    "sampleSize": min(len(logs), n_recent),
                    "streak": streak,
                    "consistency": round(consistency, 2),
                    "tier": _tier_label(confidence),
                    "rationale": rationale,
                    "gameDate": target_date,
                    "stats": {
                        "hit_rate": hr,
                        "recent": form,
                        "consistency": round(consistency, 2),
                        "streak": streak,
                    },
                }
            )
        except Exception:
            continue

    best_per_stat: Dict[str, Dict] = {}
    for r in results:
        key = r["type"]
        if key not in best_per_stat or r["confidence"] > best_per_stat[key]["confidence"]:
            best_per_stat[key] = r

    return list(best_per_stat.values()), logs


class BestPicksService:
    @staticmethod
    def get_top_picks(
        date: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 12,
        min_confidence: float = 62.0,
    ) -> Dict[str, Any]:
        season = season or "2025-26"
        target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        games = NBADataService.fetch_todays_games() or []
        games = [g for g in games if g.get("home") and g.get("away")]
        if not games:
            return {
                "items": [],
                "total": 0,
                "returned": 0,
                "date": target_date,
                "season": season,
                "message": "No games scheduled for today",
            }

        team_abbrs = set()
        opponent_by_abbr: Dict[str, str] = {}
        for g in games:
            h, a = g.get("home"), g.get("away")
            if h:
                team_abbrs.add(h)
            if a:
                team_abbrs.add(a)
            if h and a:
                opponent_by_abbr[h] = a
                opponent_by_abbr[a] = h

        teams = NBADataService.fetch_all_teams() or []
        abbr_to_id = {t.get("abbreviation"): t.get("id") for t in teams if t.get("abbreviation")}
        id_to_abbr = {t.get("id"): t.get("abbreviation") for t in teams if t.get("id") and t.get("abbreviation")}
        team_ids = {abbr_to_id[a] for a in team_abbrs if a in abbr_to_id and abbr_to_id[a]}

        from .team_player_service import TeamPlayerService
        from .context_collector import ContextCollector

        def_ranks = ContextCollector._calculate_defensive_ranks(season) or {}
        pos_ranks = ContextCollector._calculate_position_defensive_ranks(season) or {}
        team_id_to_opp_ranks: Dict[int, Dict[str, int]] = {}
        for tid in team_ids:
            tid_n = int(tid) if tid is not None else None
            if tid_n is None:
                continue
            abbr = id_to_abbr.get(tid_n)
            opp_abbr = opponent_by_abbr.get(abbr) if abbr else None
            opp_id = abbr_to_id.get(opp_abbr) if opp_abbr else None
            if opp_id is not None:
                team_id_to_opp_ranks[tid_n] = def_ranks.get(int(opp_id), {})

        team_ids_int = {TeamPlayerService.normalize_team_id(t) for t in team_ids}
        team_ids_int.discard(None)

        all_players = NBADataService.fetch_all_players_including_rookies() or []
        todays_players = [
            p
            for p in all_players
            if TeamPlayerService.normalize_team_id(p.get("team_id")) in team_ids_int
        ]

        all_picks: List[Dict] = []
        lock = threading.Lock()

        pace_ranks = ContextCollector._calculate_pace_ranks(season) or {}

        def _process(player: Dict) -> List[Dict]:
            pid = player.get("id")
            pname = player.get("full_name", "Unknown")
            if not pid:
                return []
            t_id = TeamPlayerService.normalize_team_id(player.get("team_id"))
            opp_ranks = team_id_to_opp_ranks.get(t_id) if t_id is not None else None
            opp_pos_def_ranks: Optional[Dict[str, int]] = None
            opp_id: Optional[int] = None
            opp_abbr: Optional[str] = None
            if t_id is not None:
                abbr = id_to_abbr.get(t_id)
                opp_abbr = opponent_by_abbr.get(abbr) if abbr else None
                opp_id = abbr_to_id.get(opp_abbr) if opp_abbr else None
                position = _normalize_position(player.get("position"))
                if position and opp_id is not None:
                    opp_pos_def_ranks = pos_ranks.get(position, {}).get(int(opp_id), {})
            picks, logs = _scan_player(
                pid, pname, season, target_date,
                opponent_def_ranks=opp_ranks,
                opponent_pos_def_ranks=opp_pos_def_ranks,
            )
            if not picks:
                return []
            opp_id_int = int(opp_id) if opp_id is not None else None
            position = _normalize_position(player.get("position"))
            for p in picks:
                if not opp_id_int:
                    p["matchup_score"] = None
                    p["insight_type"] = None
                    p["matchup_explanation"] = None
                    p["opponent_abbr"] = opp_abbr
                    p["opponent_def_rank_vs_position"] = None
                    p["supporting_metrics"] = None
                    continue
                stat_key = TYPE_TO_STAT.get(p.get("type"), "pts")
                try:
                    score, insight_type, matchup_explanation, opp_def_rank_vs_pos, supporting_metrics = compute_matchup_score(
                        pid,
                        stat_key,
                        logs,
                        opp_id_int,
                        position,
                        opp_ranks,
                        opp_pos_def_ranks,
                        pace_ranks,
                        season,
                        target_date,
                        player_name=pname,
                        opponent_abbr=opp_abbr,
                    )
                    p["matchup_score"] = score
                    p["insight_type"] = insight_type
                    p["matchup_explanation"] = matchup_explanation
                    p["opponent_abbr"] = opp_abbr
                    p["opponent_def_rank_vs_position"] = opp_def_rank_vs_pos
                    p["supporting_metrics"] = supporting_metrics
                except Exception:
                    p["matchup_score"] = None
                    p["insight_type"] = None
                    p["matchup_explanation"] = None
                    p["opponent_abbr"] = opp_abbr
                    p["opponent_def_rank_vs_position"] = None
                    p["supporting_metrics"] = None
            return picks

        with ThreadPoolExecutor(max_workers=12) as pool:
            futures = {pool.submit(_process, p): p for p in todays_players}
            for fut in as_completed(futures):
                try:
                    picks = fut.result(timeout=8.0)
                    if picks:
                        with lock:
                            all_picks.extend(picks)
                except Exception:
                    continue

        # Filter to higher-confidence picks only (strong+ by default; 62+ = strong/lock)
        all_picks = [p for p in all_picks if (p.get("confidence") or 0) >= min_confidence]

        # Sort by confidence descending, then hit rate
        all_picks.sort(
            key=lambda x: (x.get("confidence", 0), x.get("hitRate", 0)),
            reverse=True,
        )

        # Dynamic threshold — ensure we always return picks when games exist
        if len(all_picks) == 0:
            return {
                "items": [],
                "total": 0,
                "returned": 0,
                "date": target_date,
                "season": season,
                "message": "Data is being generated — check back soon",
            }

        top = all_picks[:limit]

        return {
            "items": top,
            "total": len(all_picks),
            "returned": len(top),
            "date": target_date,
            "season": season,
            "min_confidence": min_confidence,
        }
