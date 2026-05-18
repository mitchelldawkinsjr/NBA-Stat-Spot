"""Games table upserts."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...models.games import Game


def upsert_game(db: Session, data: Dict[str, Any]) -> Game:
    game_id = str(data["game_id"])
    row = db.query(Game).filter(Game.game_id == game_id).first()
    if not row:
        row = Game(game_id=game_id)
        db.add(row)
    row.game_date = data.get("game_date") or row.game_date
    row.season = data.get("season") or row.season or ""
    row.home_team_abbr = data.get("home_team_abbr") or row.home_team_abbr or ""
    row.away_team_abbr = data.get("away_team_abbr") or row.away_team_abbr or ""
    if data.get("home_score") is not None:
        row.home_score = int(data["home_score"])
    if data.get("away_score") is not None:
        row.away_score = int(data["away_score"])
    if data.get("status"):
        row.status = str(data["status"])
    if data.get("source"):
        row.source = str(data["source"])
    db.flush()
    return row


def list_games_for_dates(
    db: Session,
    from_date: date,
    to_date: date,
    *,
    status: Optional[str] = None,
) -> List[Game]:
    q = db.query(Game).filter(Game.game_date >= from_date, Game.game_date <= to_date)
    if status:
        q = q.filter(Game.status == status)
    return q.order_by(Game.game_date).all()
