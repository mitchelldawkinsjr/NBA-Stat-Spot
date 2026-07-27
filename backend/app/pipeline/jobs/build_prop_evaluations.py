"""Build player_prop_evaluations for a slate date from live calculator (once per night)."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...models.player_prop_evaluations import PlayerPropEvaluation
from ...services.analytics_constants import FORMULA_VERSION
from ...services.best_picks_service import TIER_LEAN, TIER_LOCK, TIER_STRONG, _tier_label
from ...services.daily_props_service import DailyPropsService
from ...utils.season import get_current_season
from ..context import PipelineContext


def _stat_key_from_type(display_type: str) -> str:
    m = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm", "PRA": "pra"}
    return m.get((display_type or "").upper(), (display_type or "").lower())


def _upsert_evaluation(
    db: Session,
    *,
    game_date: date,
    season: str,
    item: Dict[str, Any],
    pipeline_run_id: Optional[int],
) -> None:
    player_id = item.get("playerId") or item.get("player_id")
    if not player_id:
        return
    display = item.get("type") or "PTS"
    stat_type = _stat_key_from_type(str(display))
    direction = (item.get("suggestion") or "over").lower()
    line = float(item.get("marketLine") or item.get("fairLine") or 0)
    fair = item.get("fairLine")
    conf = float(item.get("confidence") or 0)
    stats = item.get("stats") or {}
    hit_rate = stats.get("hit_rate") if isinstance(stats, dict) else None

    row = (
        db.query(PlayerPropEvaluation)
        .filter_by(
            game_date=game_date,
            player_id=int(player_id),
            stat_type=stat_type,
            line=line,
            direction=direction,
        )
        .first()
    )
    if not row:
        row = PlayerPropEvaluation(
            game_date=game_date,
            player_id=int(player_id),
            stat_type=stat_type,
            line=line,
            direction=direction,
        )
        db.add(row)

    row.season = season
    row.player_name = item.get("playerName") or item.get("player_name")
    row.display_type = str(display).upper()
    row.fair_line = float(fair) if fair is not None else line
    row.market_line = float(item.get("marketLine") or line)
    row.suggestion = direction
    row.confidence = conf
    row.hit_rate = float(hit_rate) if hit_rate is not None else None
    row.tier = _tier_label(conf)
    row.is_hot = bool(item.get("isHot"))
    rationale = item.get("rationale")
    if isinstance(rationale, dict):
        rationale = rationale.get("summary") or ""
    row.rationale = str(rationale or "")[:2000]
    try:
        row.stats_json = json.dumps(stats)
    except (TypeError, ValueError):
        row.stats_json = None
    row.confidence_source = item.get("confidenceSource")
    row.rationale_source = item.get("rationaleSource")
    row.ml_available = bool(item.get("mlAvailable"))
    row.formula_version = FORMULA_VERSION
    row.computed_at = datetime.utcnow()
    row.pipeline_run_id = pipeline_run_id


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    snapshot_date = ctx.target_date or date.today()
    ds = snapshot_date.isoformat()

    # Force live compute (do not read existing prop evaluation rows).
    daily = DailyPropsService.get_top_props_for_date(
        date=ds,
        season=season,
        min_confidence=0.0,
        limit=500,
        prefer_precomputed=False,
    )
    items: List[Dict[str, Any]] = daily.get("items") or []

    written = 0
    for item in items:
        try:
            _upsert_evaluation(
                db,
                game_date=snapshot_date,
                season=season,
                item=item,
                pipeline_run_id=ctx.run_id,
            )
            written += 1
        except Exception:
            continue
    db.flush()

    return {
        "rows_written": written,
        "game_date": ds,
        "season": season,
        "formula_version": FORMULA_VERSION,
        "tier_thresholds": {"lock": TIER_LOCK, "strong": TIER_STRONG, "lean": TIER_LEAN},
    }
