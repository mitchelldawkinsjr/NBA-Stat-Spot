"""Backfill player game stats needed to settle open prop predictions.

Uses ESPN scoreboard + box scores for each pending prediction date
(far fewer API calls than per-player season crawls).
"""
from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from ...models.prediction_accuracy import PropPredictionRecord
from ...services.espn_api_service import get_espn_service
from ...services.nba_api_service import NBADataService
from ...utils.season import get_current_season
from ..context import PipelineContext
from ..repositories import player_stats_repo
from ..utils.player_match import build_name_team_index
from .ingest_boxscores import _parse_boxscore_players, log_cache_row


def _pending_dates(db: Session) -> List[date]:
    rows = (
        db.query(PropPredictionRecord.record_date)
        .filter(
            PropPredictionRecord.actual_value.is_(None),
            PropPredictionRecord.settled_at.is_(None),
        )
        .distinct()
        .order_by(PropPredictionRecord.record_date.asc())
        .all()
    )
    return [r[0] for r in rows if r[0] is not None]


def _pending_player_ids_for_date(db: Session, d: date) -> Set[int]:
    rows = (
        db.query(PropPredictionRecord.player_id)
        .filter(
            PropPredictionRecord.record_date == d,
            PropPredictionRecord.actual_value.is_(None),
            PropPredictionRecord.settled_at.is_(None),
        )
        .distinct()
        .all()
    )
    return {int(r[0]) for r in rows if r[0] is not None}


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    dates = _pending_dates(db)
    if not dates:
        return {
            "rows_written": 0,
            "dates_targeted": 0,
            "games_processed": 0,
            "errors": 0,
            "season": season,
        }

    all_players = NBADataService.fetch_all_players_including_rookies() or []
    player_index = build_name_team_index(all_players)
    espn = get_espn_service()

    stats_written = 0
    games_processed = 0
    errors = 0
    dates_done = 0

    for d in dates:
        needed = _pending_player_ids_for_date(db, d)
        if not needed:
            continue
        espn_date = d.strftime("%Y%m%d")
        try:
            board = espn.get_scoreboard(date=espn_date) or {}
        except Exception:
            errors += 1
            time.sleep(0.5)
            continue

        events = board.get("events") or []
        if not events:
            dates_done += 1
            time.sleep(0.2)
            continue

        for event in events:
            eid = str(event.get("id") or "")
            if not eid:
                continue
            # Only completed games
            comp = (event.get("competitions") or [{}])[0]
            st = ((comp.get("status") or {}).get("type") or {})
            state = (st.get("state") or "").lower()
            completed = bool(st.get("completed")) or state == "post"
            if not completed:
                continue

            try:
                summary = espn.get_game_summary(eid)
            except Exception:
                errors += 1
                continue
            if not summary:
                errors += 1
                continue

            players = _parse_boxscore_players(summary, player_index)
            if not players:
                errors += 1
                continue

            competitors = comp.get("competitors") or []
            home = away = ""
            for c in competitors:
                abbr = ((c.get("team") or {}).get("abbreviation") or "").upper()
                ha = (c.get("homeAway") or "").lower()
                if ha == "home":
                    home = abbr
                elif ha == "away":
                    away = abbr
            games_processed += 1
            touched: Set[int] = set()
            for p in players:
                pid = int(p["player_id"])
                # Always write stats (helps future settles); prioritize needed players.
                try:
                    player_stats_repo.upsert_player_game_stat(
                        db,
                        player_id=pid,
                        game_id=eid,
                        game_date=d,
                        season=season,
                        stats=p,
                        source="espn",
                    )
                    stats_written += 1
                    touched.add(pid)
                except Exception:
                    errors += 1
                    continue

                try:
                    player_stats_repo.merge_game_into_log_cache(
                        db,
                        player_id=pid,
                        season=season,
                        row=log_cache_row(
                            p, game_id=eid, game_date=d, home_abbr=home, away_abbr=away
                        ),
                    )
                except Exception:
                    pass

            db.commit()
            for pid in touched:
                NBADataService.invalidate_player_game_log(pid, season)
            time.sleep(0.15)  # gentle on ESPN rate limit

        dates_done += 1
        time.sleep(0.35)

    return {
        "rows_written": stats_written,
        "dates_targeted": len(dates),
        "dates_processed": dates_done,
        "games_processed": games_processed,
        "errors": errors,
        "season": season,
    }
