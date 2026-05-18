"""Ingest game schedule into games table."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import games_repo


def _normalize_game(g: Dict[str, Any], season: str, game_date: date) -> Dict[str, Any]:
    status = (g.get("status") or "SCHEDULED").upper()
    if status in ("FINAL", "FT", "END"):
        status = "FINAL"
    elif status in ("LIVE", "IN_PROGRESS", "IN PROGRESS"):
        status = "LIVE"
    else:
        status = "SCHEDULED"
    return {
        "game_id": str(g.get("gameId") or g.get("game_id") or ""),
        "game_date": game_date,
        "season": season,
        "home_team_abbr": (g.get("home") or g.get("home_abbr") or "").upper(),
        "away_team_abbr": (g.get("away") or g.get("away_abbr") or "").upper(),
        "home_score": g.get("homeScore") or g.get("home_score"),
        "away_score": g.get("awayScore") or g.get("away_score"),
        "status": status,
        "source": g.get("source") or "nba",
    }


def _ingest_date(db: Session, d: date, season: str) -> int:
    games = NBADataService.fetch_games_for_date(d) or []
    if not games:
        games = NBADataService.fetch_todays_games() if d == date.today() else []
    n = 0
    for g in games:
        gid = str(g.get("gameId") or g.get("game_id") or "")
        if not gid:
            continue
        payload = _normalize_game(g, season, d)
        if not payload["home_team_abbr"] or not payload["away_team_abbr"]:
            continue
        games_repo.upsert_game(db, payload)
        n += 1
    return n


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    today = date.today()
    if ctx.from_date and ctx.to_date:
        dates = []
        d = ctx.from_date
        while d <= ctx.to_date:
            dates.append(d)
            d += timedelta(days=1)
    else:
        anchor = ctx.target_date or today
        dates = [anchor - timedelta(days=1), anchor]

    total = 0
    for d in dates:
        total += _ingest_date(db, d, season)

    return {
        "rows_written": total,
        "dates": [d.isoformat() for d in dates],
        "last_game_date": dates[-1].isoformat() if dates else None,
        "season": season,
    }
