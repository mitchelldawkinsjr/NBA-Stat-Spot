"""Resolve a useful slate date when today has no games (offseason / gaps)."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...models.player_game_stats import PlayerGameStat
from ...models.player_prop_evaluations import PlayerPropEvaluation


def resolve_slate_date(
    db: Session,
    *,
    target_date: Optional[date] = None,
    season: Optional[str] = None,
) -> date:
    """
    Prefer an explicit target_date; otherwise today if prop rows exist for today;
    else the latest prop-evaluation date; else the latest player_game_stats date;
    else today.
    """
    if target_date is not None:
        return target_date

    today = date.today()
    today_props = (
        db.query(func.count(PlayerPropEvaluation.id))
        .filter(PlayerPropEvaluation.game_date == today)
        .scalar()
        or 0
    )
    if today_props > 0:
        return today

    q_props = db.query(func.max(PlayerPropEvaluation.game_date))
    if season:
        q_props = q_props.filter(PlayerPropEvaluation.season == season)
    latest_props = q_props.scalar()
    if latest_props:
        return latest_props

    q_stats = db.query(func.max(PlayerGameStat.game_date))
    if season:
        q_stats = q_stats.filter(PlayerGameStat.season == season)
    latest_stats = q_stats.scalar()
    if latest_stats:
        return latest_stats

    return today
