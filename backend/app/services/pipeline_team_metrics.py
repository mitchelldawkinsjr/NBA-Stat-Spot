"""Team PPG, pace, and off/def ranks from pipeline tables.

Game pages should read these instead of the NBA-API league-average fallback
(112.5 PPG) or the 5-player possession estimate that collapses to a handful
of turnovers when shooting columns are missing.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.games import Game
from ..models.player_game_log_cache import PlayerGameLogCache
from ..models.player_game_stats import PlayerGameStat
from ..models.teams import Team
from .box_score_validator import BoxScoreValidator
from .cache_service import get_cache_service

# Real NBA pace is ~95–105. Values below this are partial player samples, not possessions.
MIN_POSSESSIONS = 70.0
CACHE_TTL = 6 * 3600

_MATCHUP_RE = re.compile(r"([A-Z]{2,5})\s+(VS|@)\s+([A-Z]{2,5})")
_TO_CANON = {
    "SA": "SAS",
    "NO": "NOP",
    "GS": "GSW",
    "NY": "NYK",
    "UTAH": "UTA",
    "WSH": "WAS",
    "PHO": "PHX",
    "BRK": "BKN",
}
_FROM_CANON = {v: k for k, v in _TO_CANON.items()}


def canon_abbr(abbr: Optional[str]) -> str:
    if not abbr:
        return ""
    u = abbr.strip().upper()
    return _TO_CANON.get(u, u)


def abbr_keys(abbr: Optional[str]) -> List[str]:
    raw = (abbr or "").strip().upper()
    if not raw:
        return []
    canon = canon_abbr(raw)
    keys = {raw, canon}
    extra = _FROM_CANON.get(canon)
    if extra:
        keys.add(extra)
    return [k for k in keys if k]


def _avg(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _ranks(averages: Dict[str, float], *, higher_is_better: bool) -> Dict[str, int]:
    ordered = sorted(averages.items(), key=lambda item: item[1], reverse=higher_is_better)
    return {abbr: rank for rank, (abbr, _) in enumerate(ordered, start=1)}


def _parse_matchup(matchup: Optional[str]) -> Optional[tuple]:
    if not matchup:
        return None
    text = matchup.upper().replace("VS.", "VS").replace("V.", "VS")
    match = _MATCHUP_RE.search(text)
    if not match:
        return None
    team = canon_abbr(match.group(1))
    is_home = match.group(2) == "VS"
    opp = canon_abbr(match.group(3))
    if not team or not opp:
        return None
    return team, opp, is_home


def compute_pipeline_team_metrics(db: Session, season: str) -> Dict[str, Any]:
    """Return {by_abbr, by_id} team scoring from games + cached box rows."""
    teams = db.query(Team).all()
    abbr_to_id: Dict[str, int] = {}
    for team in teams:
        if team.id is None or not team.abbreviation:
            continue
        for key in abbr_keys(team.abbreviation):
            abbr_to_id[key] = int(team.id)

    games = (
        db.query(Game)
        .filter(
            Game.season == season,
            Game.home_score.isnot(None),
            Game.away_score.isnot(None),
            Game.status == "FINAL",
        )
        .all()
    )

    scored: Dict[str, List[float]] = {}
    allowed: Dict[str, List[float]] = {}
    for game in games:
        home = canon_abbr(game.home_team_abbr)
        away = canon_abbr(game.away_team_abbr)
        if not home or not away:
            continue
        scored.setdefault(home, []).append(float(game.home_score))
        scored.setdefault(away, []).append(float(game.away_score))
        allowed.setdefault(home, []).append(float(game.away_score))
        allowed.setdefault(away, []).append(float(game.home_score))

    # Box rows carry FGA/FTA/OREB and a matchup string. player_game_stats does not.
    logs = (
        db.query(PlayerGameLogCache)
        .filter(PlayerGameLogCache.season == season)
        .all()
    )
    boxes: Dict[str, Dict[str, Dict[str, float]]] = {}
    for row in logs:
        parsed = _parse_matchup(row.matchup)
        if not parsed:
            continue
        team, opp, _is_home = parsed
        slot = boxes.setdefault(str(row.game_id), {})
        side = slot.setdefault(
            team,
            {"fga": 0.0, "fta": 0.0, "tov": 0.0, "oreb": 0.0, "reb": 0.0, "ast": 0.0, "3pm": 0.0, "n": 0.0, "opp": opp},
        )
        side["fga"] += float(row.fga or 0)
        side["fta"] += float(row.fta or 0)
        side["tov"] += float(row.tov or 0)
        side["oreb"] += float(row.oreb or 0)
        side["reb"] += float(row.reb or 0)
        side["ast"] += float(row.ast or 0)
        side["3pm"] += float(row.tpm or 0)
        side["n"] += 1

    # Fill reb/ast/3pm from player_game_stats when the log cache has no matchup.
    if not boxes:
        stat_rows = (
            db.query(PlayerGameStat)
            .filter(
                PlayerGameStat.season == season,
                or_(
                    PlayerGameStat.validation_status.is_(None),
                    PlayerGameStat.validation_status != BoxScoreValidator.STATUS_INVALID,
                ),
            )
            .all()
        )
        game_by_id = {g.game_id: g for g in games}
        for row in stat_rows:
            game = game_by_id.get(row.game_id)
            if not game or row.is_home is None:
                continue
            team = canon_abbr(game.home_team_abbr if row.is_home else game.away_team_abbr)
            opp = canon_abbr(game.away_team_abbr if row.is_home else game.home_team_abbr)
            if not team:
                continue
            slot = boxes.setdefault(str(row.game_id), {})
            side = slot.setdefault(
                team,
                {"fga": 0.0, "fta": 0.0, "tov": 0.0, "oreb": 0.0, "reb": 0.0, "ast": 0.0, "3pm": 0.0, "n": 0.0, "opp": opp},
            )
            side["fga"] += float(row.field_goals_attempted or 0)
            side["tov"] += float(row.turnovers or 0)
            side["reb"] += float(row.rebounds or 0)
            side["ast"] += float(row.assists or 0)
            side["3pm"] += float(row.three_pointers_made or 0)
            side["n"] += 1

    off_reb: Dict[str, List[float]] = {}
    off_ast: Dict[str, List[float]] = {}
    off_3pm: Dict[str, List[float]] = {}
    def_reb: Dict[str, List[float]] = {}
    def_ast: Dict[str, List[float]] = {}
    def_3pm: Dict[str, List[float]] = {}
    pace_vals: Dict[str, List[float]] = {}

    for sides in boxes.values():
        for team, side in sides.items():
            if side["n"] < 5:
                continue
            off_reb.setdefault(team, []).append(side["reb"])
            off_ast.setdefault(team, []).append(side["ast"])
            off_3pm.setdefault(team, []).append(side["3pm"])
            poss = side["fga"] + 0.44 * side["fta"] + side["tov"] - side["oreb"]
            if poss >= MIN_POSSESSIONS:
                pace_vals.setdefault(team, []).append(poss)
            opp_side = sides.get(side.get("opp") or "")
            if opp_side and opp_side["n"] >= 5:
                def_reb.setdefault(team, []).append(opp_side["reb"])
                def_ast.setdefault(team, []).append(opp_side["ast"])
                def_3pm.setdefault(team, []).append(opp_side["3pm"])

    ppg_avg = {abbr: _avg(vals) for abbr, vals in scored.items() if vals}
    pa_avg = {abbr: _avg(vals) for abbr, vals in allowed.items() if vals}
    off_pts_rank = _ranks(ppg_avg, higher_is_better=True)
    def_pts_rank = _ranks(pa_avg, higher_is_better=False)
    off_reb_rank = _ranks({a: _avg(v) for a, v in off_reb.items() if v}, higher_is_better=True)
    off_ast_rank = _ranks({a: _avg(v) for a, v in off_ast.items() if v}, higher_is_better=True)
    off_3pm_rank = _ranks({a: _avg(v) for a, v in off_3pm.items() if v}, higher_is_better=True)
    def_reb_rank = _ranks({a: _avg(v) for a, v in def_reb.items() if v}, higher_is_better=False)
    def_ast_rank = _ranks({a: _avg(v) for a, v in def_ast.items() if v}, higher_is_better=False)
    def_3pm_rank = _ranks({a: _avg(v) for a, v in def_3pm.items() if v}, higher_is_better=False)
    pace_avg = {abbr: _avg(vals) for abbr, vals in pace_vals.items() if vals}
    pace_rank = _ranks(pace_avg, higher_is_better=True)

    all_abbrs = set(ppg_avg) | set(pace_avg) | set(off_reb_rank) | set(abbr_to_id)
    by_abbr: Dict[str, Dict[str, Any]] = {}
    by_id: Dict[int, Dict[str, Any]] = {}

    for abbr in all_abbrs:
        off = {
            "pts": off_pts_rank.get(abbr),
            "reb": off_reb_rank.get(abbr),
            "ast": off_ast_rank.get(abbr),
            "3pm": off_3pm_rank.get(abbr),
        }
        deff = {
            "pts": def_pts_rank.get(abbr),
            "reb": def_reb_rank.get(abbr),
            "ast": def_ast_rank.get(abbr),
            "3pm": def_3pm_rank.get(abbr),
        }
        off = {k: v for k, v in off.items() if v is not None}
        deff = {k: v for k, v in deff.items() if v is not None}
        ppg = ppg_avg.get(abbr)
        poss = pace_avg.get(abbr)
        record = {
            "abbr": abbr,
            "ppg": round(ppg, 1) if ppg is not None else None,
            "points_allowed": round(pa_avg[abbr], 1) if abbr in pa_avg and pa_avg[abbr] is not None else None,
            "possessions": round(poss, 1) if poss is not None else None,
            "pace_rank": pace_rank.get(abbr),
            "games": len(scored.get(abbr) or []),
            "off": off,
            "def": deff,
        }
        if record["ppg"] is None and not off and not deff and record["possessions"] is None:
            continue
        for key in abbr_keys(abbr):
            by_abbr[key] = record
        tid = abbr_to_id.get(abbr)
        if tid is not None:
            by_id[tid] = record

    return {"by_abbr": by_abbr, "by_id": by_id, "season": season}


def get_pipeline_team_metrics(
    season: str,
    db: Optional[Session] = None,
    *,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    cache = get_cache_service()
    cache_key = f"pipeline_team_metrics:{season}:6h"
    if not force_refresh:
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and (cached.get("by_abbr") or cached.get("by_id")):
            return cached

    own_session = db is None
    session = db or SessionLocal()
    try:
        payload = compute_pipeline_team_metrics(session, season)
    finally:
        if own_session:
            session.close()

    if payload.get("by_abbr") or payload.get("by_id"):
        cache.set(cache_key, payload, ttl=CACHE_TTL)
    return payload


def publish_rank_caches(season: str, metrics: Dict[str, Any]) -> Dict[str, int]:
    """Write pipeline ranks into the cache keys game predictions already read."""
    by_id: Dict[int, Dict[str, Any]] = metrics.get("by_id") or {}
    if len(by_id) < 8:
        return {"teams": len(by_id)}

    def_ranks: Dict[int, Dict[str, int]] = {}
    off_ranks: Dict[int, Dict[str, int]] = {}
    pace_ranks: Dict[int, Dict[str, Any]] = {}
    for tid, row in by_id.items():
        if row.get("def"):
            def_ranks[int(tid)] = row["def"]
        if row.get("off"):
            off_ranks[int(tid)] = row["off"]
        if row.get("possessions") is not None:
            pace_ranks[int(tid)] = {
                "possessions": row["possessions"],
                "pace_rank": row.get("pace_rank"),
            }

    cache = get_cache_service()
    if def_ranks:
        cache.set(f"defensive_ranks:{season}:24h", def_ranks, ttl=86400)
    if off_ranks:
        cache.set(f"offensive_ranks:{season}:24h", off_ranks, ttl=86400)
    if pace_ranks:
        cache.set(f"pace_ranks:{season}:24h", pace_ranks, ttl=86400)
    return {
        "teams": len(by_id),
        "def_teams": len(def_ranks),
        "off_teams": len(off_ranks),
        "pace_teams": len(pace_ranks),
    }
