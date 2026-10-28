"""Player game stats and log cache upserts."""
from __future__ import annotations
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from ...models.game_participants import GameParticipant
from ...models.player_game_log_cache import PlayerGameLogCache
from ...models.player_game_stats import PlayerGameStat
from ...services.box_score_validator import BoxScoreValidator, validate_and_serialize


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
    # Feeds without these keys must not wipe values written by a richer source.
    for attr, short, long in (
        ("steals", "stl", "steals"),
        ("blocks", "blk", "blocks"),
        ("turnovers", "tov", "turnovers"),
    ):
        if short in stats or long in stats:
            setattr(row, attr, int(stats.get(short) or stats.get(long) or 0))
        elif getattr(row, attr) is None:
            setattr(row, attr, 0)

    if any(k in stats for k in ("fgm", "field_goals_made")):
        row.field_goals_made = int(stats.get("fgm") or stats.get("field_goals_made") or 0)
        if any(k in stats for k in ("fga", "field_goals_attempted")):
            row.field_goals_attempted = int(stats.get("fga") or stats.get("field_goals_attempted") or 0)
    elif any(k in stats for k in ("fga", "field_goals_attempted")):
        # Attempted-only feeds (e.g. game-log cache) — store FGA but do not invent FGM=0 for validation.
        row.field_goals_attempted = int(stats.get("fga") or stats.get("field_goals_attempted") or 0)
    if any(k in stats for k in ("ftm", "free_throws_made")):
        row.free_throws_made = int(stats.get("ftm") or stats.get("free_throws_made") or 0)

    validation_record: Dict[str, Any] = {
        "points": row.points,
        "rebounds": row.rebounds,
        "assists": row.assists,
        "steals": row.steals,
        "blocks": row.blocks,
        "turnovers": row.turnovers,
        "three_pointers_made": row.three_pointers_made,
        "minutes_played": row.minutes_played,
    }
    # Points identity only when made+attempted shooting fields were provided together.
    if any(k in stats for k in ("fgm", "field_goals_made")):
        validation_record["field_goals_made"] = row.field_goals_made
        validation_record["field_goals_attempted"] = row.field_goals_attempted
    if row.free_throws_made is not None and any(k in stats for k in ("ftm", "free_throws_made")):
        validation_record["free_throws_made"] = row.free_throws_made

    status, failures_json = validate_and_serialize(validation_record)
    row.validation_status = status
    row.validation_failures = failures_json

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
    # Dedupe by game_id (ESPN can return duplicates); unique is (player_id, game_id).
    by_gid: Dict[str, Dict[str, Any]] = {}
    for row in logs:
        gid = str(row.get("game_id") or "")
        if gid:
            by_gid[gid] = row

    # Remove any existing rows for these game_ids (any season) plus this season.
    gids = list(by_gid.keys())
    if gids:
        db.query(PlayerGameLogCache).filter(
            PlayerGameLogCache.player_id == player_id,
            PlayerGameLogCache.game_id.in_(gids),
        ).delete(synchronize_session=False)
    db.query(PlayerGameLogCache).filter_by(player_id=player_id, season=season).delete(
        synchronize_session=False
    )

    n = 0
    for gid, row in by_gid.items():
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


def merge_game_into_log_cache(
    db: Session,
    *,
    player_id: int,
    season: str,
    row: Dict[str, Any],
) -> int:
    """Add or replace one game in a player's cached log, keeping all other games."""
    existing = db.query(PlayerGameLogCache).filter_by(player_id=player_id, season=season).all()
    merged = {str(r.game_id): r.to_dict() for r in existing}
    for r in existing:
        db.expunge(r)
    merged[str(row["game_id"])] = row
    return sync_player_game_log_cache(
        db, player_id=player_id, season=season, logs=list(merged.values())
    )


def sync_logs_to_player_game_stats(
    db: Session,
    *,
    player_id: int,
    season: str,
    logs: List[Dict[str, Any]],
    source: str = "nba_api",
) -> int:
    """Upsert game-log rows into player_game_stats (with validation)."""
    written = 0
    for row in logs:
        gid = str(row.get("game_id") or "")
        if not gid:
            continue
        gd_raw = row.get("game_date") or ""
        try:
            if isinstance(gd_raw, date):
                gdate = gd_raw
            else:
                gdate = date.fromisoformat(str(gd_raw)[:10])
        except ValueError:
            continue
        upsert_player_game_stat(
            db,
            player_id=player_id,
            game_id=gid,
            game_date=gdate,
            season=season,
            stats=row,
            source=source,
        )
        written += 1
    return written


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


def known_player_ids(db: Session, player_ids: Set[int]) -> Set[int]:
    """Player ids that exist in players. Box-score feeds include ids we have not loaded."""
    from ...models.players import Player

    ids = {int(pid) for pid in player_ids if pid is not None}
    if not ids:
        return set()
    rows = db.query(Player.id).filter(Player.id.in_(ids)).all()
    return {int(row[0]) for row in rows}


def get_player_logs_from_stats(
    db: Session, player_id: int, season: str, limit: int = 30, exclude_invalid: bool = True
) -> List[Dict[str, Any]]:
    from sqlalchemy import or_

    q = db.query(PlayerGameStat).filter(
        PlayerGameStat.player_id == player_id, PlayerGameStat.season == season
    )
    if exclude_invalid:
        q = q.filter(
            or_(
                PlayerGameStat.validation_status.is_(None),
                PlayerGameStat.validation_status != BoxScoreValidator.STATUS_INVALID,
            )
        )
    rows = q.order_by(PlayerGameStat.game_date.desc()).limit(limit).all()
    game_ids = [r.game_id for r in rows if r.game_id]
    cache_by_game: Dict[str, PlayerGameLogCache] = {}
    if game_ids:
        for cached in (
            db.query(PlayerGameLogCache)
            .filter(
                PlayerGameLogCache.player_id == player_id,
                PlayerGameLogCache.game_id.in_(game_ids),
            )
            .all()
        ):
            cache_by_game[str(cached.game_id)] = cached
    out = []
    for r in rows:
        cached = cache_by_game.get(str(r.game_id))
        out.append(
            {
                "game_id": r.game_id,
                "game_date": r.game_date.isoformat() if r.game_date else "",
                "matchup": (cached.matchup if cached else "") or "",
                "pts": float(r.points or 0),
                "reb": float(r.rebounds or 0),
                "ast": float(r.assists or 0),
                "tpm": float(r.three_pointers_made or 0),
                "minutes": float(r.minutes_played or 0),
                "stl": float(r.steals or 0),
                "blk": float(r.blocks or 0),
                "tov": float(cached.tov if cached is not None else (r.turnovers or 0)),
                "fga": float(cached.fga or 0) if cached is not None else float(r.field_goals_attempted or 0),
                "fta": float(cached.fta or 0) if cached is not None else 0.0,
                "oreb": float(cached.oreb or 0) if cached is not None else 0.0,
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
