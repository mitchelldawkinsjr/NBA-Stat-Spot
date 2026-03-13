"""
Rule-based insight scanner for daily matchup and pace insights.
Generates human-readable alerts like "OKC allows the 2nd most PTS to PGs" or "Team plays top-3 pace".
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .context_collector import ContextCollector
from .nba_api_service import NBADataService
from ..utils.season import get_current_season


@dataclass
class InsightAlert:
    text: str
    category: str
    team_abbr: Optional[str] = None
    stat: Optional[str] = None
    rank: Optional[int] = None
    position: Optional[str] = None


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def scan_all_insights(
    date_str: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 50,
) -> List[InsightAlert]:
    """
    Scan today's games and league data to produce rule-based insight alerts.
    Examples: "OKC allows the 2nd most PTS to PGs", "Team plays top-3 pace".
    """
    season = season or get_current_season()
    alerts: List[InsightAlert] = []

    try:
        games = NBADataService.fetch_todays_games() or []
        if not games:
            return alerts
        team_abbrs = set()
        for g in games:
            if g.get("home"):
                team_abbrs.add(str(g["home"]).upper())
            if g.get("away"):
                team_abbrs.add(str(g["away"]).upper())

        teams = NBADataService.fetch_all_teams() or []
        abbr_to_id = {str(t.get("abbreviation", "")).upper(): t.get("id") for t in teams if t.get("abbreviation")}
        id_to_abbr = {v: k for k, v in abbr_to_id.items() if v is not None}

        pos_ranks = ContextCollector._calculate_position_defensive_ranks(season) or {}
        pace_ranks = ContextCollector._calculate_pace_ranks(season) or {}

        # Position defense: for each team playing today, for each position, get rank (1 = best D)
        # "Worst" for a stat = highest rank number (e.g. 30th = allows most). So "allows 2nd most" = rank 29 or 30.
        for position, team_ranks in pos_ranks.items():
            if not isinstance(team_ranks, dict):
                continue
            for team_id, ranks in team_ranks.items():
                abbr = id_to_abbr.get(int(team_id) if team_id is not None else None)
                if abbr not in team_abbrs or not isinstance(ranks, dict):
                    continue
                for stat_key, rank_val in ranks.items():
                    if rank_val is None:
                        continue
                    r = int(rank_val)
                    # Rank 28-30 = allows among most (bad defense for that stat; 30 = allows most)
                    if r >= 28:
                        n_most = 31 - r
                        rank_label = "most" if n_most == 1 else f"{_ordinal(n_most)} most"
                        stat_label = {"pts": "PTS", "reb": "REB", "ast": "AST", "3pm": "3PM"}.get(str(stat_key).lower(), str(stat_key))
                        alerts.append(InsightAlert(
                            text=f"{abbr} allows the {rank_label} {stat_label} to {position}s",
                            category="position_defense",
                            team_abbr=abbr,
                            stat=stat_label,
                            rank=r,
                            position=position,
                        ))
                if len(alerts) >= limit:
                    break
            if len(alerts) >= limit:
                break

        # Pace: top-5 pace = high pace (rank 1 = most possessions). "Plays top-3 pace" for rank 1-3.
        if len(alerts) < limit and pace_ranks:
            for team_id, pace_data in pace_ranks.items():
                abbr = id_to_abbr.get(int(team_id) if team_id is not None else None)
                if abbr not in team_abbrs:
                    continue
                pr = pace_data.get("pace_rank") if isinstance(pace_data, dict) else None
                if pr is not None and 1 <= pr <= 5:
                    alerts.append(InsightAlert(
                        text=f"{abbr} plays top-{pr} pace this season",
                        category="pace",
                        team_abbr=abbr,
                        rank=pr,
                    ))
                if len(alerts) >= limit:
                    break

    except Exception:
        pass

    return alerts[:limit]
