"""Player game stats and log cache upserts."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...models.game_participants import GameParticipant
from ...models.player_game_log_cache import PlayerGameLogCache
from ...models.player_game_stats import PlayerGameStat


def _stat_id(player_id: int, game_id: str) -> str:
    return f"{player_id}:{game_id}"


def upsert_player_game_stat(
    db: Session,
    *,
    player_id: int,
    game_id: str,
    game_date: date,
    season: str,
    stats: Dict[str, Any],
    source: str = "espn",
) -> Optional[PlayerGameStat]:
    sid = _stat_id(player_id, game_id)
    row = db.query(PlayerGameStat).filter(PlayerGameStat.id == sid).first()
    if not row:
        row = db.query(PlayerGameStat).filter(
            PlayerGameStat.player_id == player_id,
            PlayerGameStat.game_id == game_id,
        ).first()
    if not row:
        row = PlayerGameStat(id=sid, player_id=player_id, game_id=game_id)
        db.add(row)
    row.game_date = game_date
    row.season = season
    row.source = source
    row.fetched_at = datetime.utcnow()
    row.points = int(stats.get("pts") or stats.get("points") or 0)
    row.rebounds = int(stats.get("reb") or stats.get("rebounds") or 0)
    row.assists = int(stats.get("ast") or stats.get("assists") or 0)
    row.three_pointers_made = int(stats.get("tpm") or stats.get("three_pointers_made") or 0)
    row.minutes_played = float(stats.get("minutes") or stats.get("minutes_played") or 0)
    row.steals = int(stats.get("stl") or stats.get("steals") or 0)
    row.blocks = int(stats.get("blk") or stats.get("blocks") or 0)
    row.turnovers = int(stats.get("tov") or stats.get("turnovers") or 0)
    db.flush()
    return row


def sync_player_game_log_cache(
    db: Session,
    *,
    player_id: int,
    season: str,
    logs: List[Dict[str, Any]],
) -> int:
    if not logs:
        return 0
    db.query(PlayerGameLogCache).filter_by(player_id=player_id, season=season).delete(
        synchronize_session=False
    )
    n = 0
    for row in logs:
        gid = str(row.get("game_id") or "")
        if not gid:
            continue
        db.add(
            PlayerGameLogCache(
                player_id=player_id,
                season=season,
                game_id=gid,
                game_date=str(row.get("game_date", ""))[:16],
                matchup=str(row.get("matchup", "")),
                pts=float(row.get("pts", 0) or 0),
                reb=float(row.get("reb", 0) or 0),
                ast=float(row.get("ast", 0) or 0),
                tpm=float(row.get("tpm", 0) or 0),
                minutes=float(row.get("minutes", 0) or 0),
                fga=float(row.get("fga", 0) or 0),
                fta=float(row.get("fta", 0) or 0),
                tov=float(row.get("tov", 0) or 0),
                oreb=float(row.get("oreb", 0) or 0),
                stl=float(row.get("stl", 0) or 0),
                blk=float(row.get("blk", 0) or 0),
            )
        )
        n += 1
    db.flush()
    return n


def record_game_participant(db: Session, game_id: str, player_id: int) -> None:
    exists = (
        db.query(GameParticipant.id)
        .filter(GameParticipant.game_id == game_id, GameParticipant.player_id == player_id)
        .first()
    )
    if not exists:
        db.add(GameParticipant(game_id=game_id, player_id=player_id))
        db.flush()


def get_participants_for_game(db: Session, game_id: str) -> List[int]:
    rows = db.query(GameParticipant.player_id).filter(GameParticipant.game_id == game_id).all()
    return [r[0] for r in rows]


def get_player_logs_from_stats(
    db: Session, player_id: int, season: str, limit: int = 30
) -> List[Dict[str, Any]]:
    rows = (
        db.query(PlayerGameStat)
        .filter(PlayerGameStat.player_id == player_id, PlayerGameStat.season == season)
        .order_by(PlayerGameStat.game_date.desc())
        .limit(limit)
        .all()
    )
    out = []
    for r in rows:
        out.append(
            {
                "game_id": r.game_id,
                "game_date": r.game_date.isoformat() if r.game_date else "",
                "matchup": "",
                "pts": float(r.points or 0),
                "reb": float(r.rebounds or 0),
                "ast": float(r.assists or 0),
                "tpm": float(r.three_pointers_made or 0),
                "minutes": float(r.minutes_played or 0),
                "stl": float(r.steals or 0),
                "blk": float(r.blocks or 0),
                "tov": float(r.turnovers or 0),
            }
        )
    return out


def max_game_date_for_player(db: Session, player_id: int, season: str) -> Optional[date]:
    from sqlalchemy import func

    row = (
        db.query(func.max(PlayerGameStat.game_date))
        .filter(PlayerGameStat.player_id == player_id, PlayerGameStat.season == season)
        .scalar()
    )
    return row
