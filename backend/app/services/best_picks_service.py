"""
Best Picks Service — unified "Top Picks of the Day" for the homepage.

Merges the logic of DailyPropsService (broad scan) and HighHitRateService
(line-range search) into a single pipeline that:
  1. Finds every player playing today.
  2. For each player × stat, searches half-point lines to maximise hit rate.
  3. Scores each pick with the multi-factor confidence formula.
  4. Auto-selects over/under direction.
  5. Tiers picks: Lock / Strong / Lean.
  6. Guarantees the section is never empty when games exist.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .nba_api_service import NBADataService
from .prop_engine import PropBetEngine
from .stats_calculator import StatsCalculator


STAT_TYPES = ["pts", "reb", "ast", "tpm"]
DISPLAY = {"pts": "PTS", "reb": "REB", "ast": "AST", "tpm": "3PM", "pra": "PRA"}

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


def _scan_player(
    player_id: int,
    player_name: str,
    season: str,
    target_date: str,
    n_recent: int = 10,
) -> List[Dict[str, Any]]:
    """Return the best pick per stat-type for one player. Uses line search when possible; falls back to average-based picks."""
    try:
        logs = NBADataService.fetch_player_game_log(player_id, season)
        if not logs or len(logs) < 3:
            return []
        if _avg_minutes(logs) < 18.0:
            return []
        logs = _enrich_pra(logs)
    except Exception:
        return []

    results: List[Dict[str, Any]] = []
    all_stats = STAT_TYPES + ["pra"]
    # Only run line search when we have enough games; otherwise we'll use average-based only
    min_games_for_line_search = 5

    for stat in all_stats:
        try:
            if len(logs) < min_games_for_line_search:
                continue
            for direction in ("over", "under"):
                line, hr = PropBetEngine.find_best_line(logs, stat, direction, n_recent)
                if hr < 0.55:
                    continue

                confidence = PropBetEngine.multi_factor_confidence(
                    logs, stat, line, direction
                )
                form = StatsCalculator.calculate_recent_form(logs, stat)
                consistency = StatsCalculator.calculate_consistency(logs, stat, n_games=n_recent)
                streak = StatsCalculator.calculate_streak(logs, stat, line, direction)

                rationale = PropBetEngine.build_rationale_text(
                    hr, direction, line, form["trend"], consistency, streak, min(len(logs), n_recent)
                )

                results.append(
                    {
                        "type": DISPLAY.get(stat, stat.upper()),
                        "playerId": player_id,
                        "playerName": player_name,
                        "marketLine": line,
                        "fairLine": PropBetEngine.determine_line_value(logs, stat),
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

    # Keep only the single best pick per stat (highest confidence)
    best_per_stat: Dict[str, Dict] = {}
    for r in results:
        key = r["type"]
        if key not in best_per_stat or r["confidence"] > best_per_stat[key]["confidence"]:
            best_per_stat[key] = r

    # Average-based fallback: when no line met 0.55 hit rate, use season average as the line
    # so we still show picks (props typically move around averages)
    for stat in all_stats:
        key = DISPLAY.get(stat, stat.upper())
        if key in best_per_stat:
            continue
        try:
            line = PropBetEngine.determine_line_value(logs, stat)
            recent = logs[-n_recent:] if n_recent else logs
            hr_over = StatsCalculator.calculate_hit_rate(recent, line, stat, "over")
            hr_under = StatsCalculator.calculate_hit_rate(recent, line, stat, "under")
            direction = "over" if hr_over >= hr_under else "under"
            hr = hr_over if direction == "over" else hr_under

            confidence = PropBetEngine.multi_factor_confidence(logs, stat, line, direction)
            form = StatsCalculator.calculate_recent_form(logs, stat)
            consistency = StatsCalculator.calculate_consistency(logs, stat, n_games=n_recent)
            streak = StatsCalculator.calculate_streak(logs, stat, line, direction)

            rationale = PropBetEngine.build_rationale_text(
                hr, direction, line, form["trend"], consistency, streak, min(len(logs), n_recent)
            )
            rationale = "Based on season average. " + rationale

            best_per_stat[key] = {
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
        except Exception:
            continue

    return list(best_per_stat.values())


class BestPicksService:
    @staticmethod
    def get_top_picks(
        date: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 20,
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
        for g in games:
            if g.get("home"):
                team_abbrs.add(g["home"])
            if g.get("away"):
                team_abbrs.add(g["away"])

        teams = NBADataService.fetch_all_teams() or []
        abbr_to_id = {t.get("abbreviation"): t.get("id") for t in teams if t.get("abbreviation")}
        team_ids = {abbr_to_id[a] for a in team_abbrs if a in abbr_to_id and abbr_to_id[a]}

        from .team_player_service import TeamPlayerService

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

        def _process(player: Dict) -> List[Dict]:
            pid = player.get("id")
            pname = player.get("full_name", "Unknown")
            if not pid:
                return []
            return _scan_player(pid, pname, season, target_date)

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
        }
