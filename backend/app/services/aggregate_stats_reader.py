"""Read-only accessors for precomputed analytics tables.

Missing rows return None / empty — never invent league averages.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models.player_line_hit_rates import PlayerLineHitRate
from ..models.player_opponent_analysis import PlayerOpponentAnalysis
from ..models.player_prop_evaluations import PlayerPropEvaluation
from ..models.player_stat_windows import PlayerStatWindow


class AggregateStatsReader:
    @staticmethod
    def get_stat_window(
        db: Session,
        player_id: int,
        season: str,
        stat_type: str,
        window: str,
    ) -> Optional[Dict[str, Any]]:
        row = (
            db.query(PlayerStatWindow)
            .filter_by(
                player_id=player_id,
                season=season,
                stat_type=stat_type,
                window=window,
            )
            .first()
        )
        if not row:
            return None
        return {
            "player_id": row.player_id,
            "season": row.season,
            "stat_type": row.stat_type,
            "window": row.window,
            "avg": row.avg,
            "weighted_avg": row.weighted_avg,
            "trend": row.trend,
            "trend_slope": row.trend_slope,
            "consistency": row.consistency,
            "heat_index": row.heat_index,
            "volatility_index": row.volatility_index,
            "games_sample": row.games_sample,
            "formula_version": row.formula_version,
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        }

    @staticmethod
    def list_stat_windows(
        db: Session, player_id: int, season: str, stat_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        q = db.query(PlayerStatWindow).filter_by(player_id=player_id, season=season)
        if stat_type:
            q = q.filter_by(stat_type=stat_type)
        return [
            {
                "stat_type": r.stat_type,
                "window": r.window,
                "avg": r.avg,
                "weighted_avg": r.weighted_avg,
                "trend": r.trend,
                "trend_slope": r.trend_slope,
                "consistency": r.consistency,
                "heat_index": r.heat_index,
                "volatility_index": r.volatility_index,
                "games_sample": r.games_sample,
            }
            for r in q.all()
        ]

    @staticmethod
    def get_hit_rate(
        db: Session,
        player_id: int,
        season: str,
        stat_type: str,
        line: float,
        direction: str,
        window: str,
    ) -> Optional[Dict[str, Any]]:
        row = (
            db.query(PlayerLineHitRate)
            .filter_by(
                player_id=player_id,
                season=season,
                stat_type=stat_type,
                line=line,
                direction=direction,
                window=window,
            )
            .first()
        )
        if not row:
            # Tolerate float key drift: match nearest line within 0.01
            candidates = (
                db.query(PlayerLineHitRate)
                .filter_by(
                    player_id=player_id,
                    season=season,
                    stat_type=stat_type,
                    direction=direction,
                    window=window,
                )
                .all()
            )
            row = next((c for c in candidates if abs(float(c.line) - float(line)) < 0.01), None)
        if not row:
            return None
        return {
            "hit_rate": row.hit_rate,
            "hit_rate_percentage": round(100 * (row.hit_rate or 0)),
            "hits": row.hits,
            "total": row.total,
            "line": row.line,
            "direction": row.direction,
            "window": row.window,
        }

    @staticmethod
    def trend_block_for_line(
        db: Session,
        player_id: int,
        season: str,
        stat_type: str,
        line: float,
        direction: str,
        windows: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build L5/L10/L20-style trend dict from precomputed hit rates."""
        labels = {"l5": "L5", "l10": "L10", "l20": "L20"}
        use = windows or ["l5", "l10", "l20"]
        out: Dict[str, Any] = {}
        for w in use:
            hr = AggregateStatsReader.get_hit_rate(
                db, player_id, season, stat_type, line, direction, w
            )
            label = labels.get(w, w.upper())
            if hr:
                out[label] = {
                    "hit_rate_percentage": hr["hit_rate_percentage"],
                    "hits": hr["hits"],
                    "total": hr["total"],
                    "results": [],
                }
            else:
                out[label] = {
                    "hit_rate_percentage": 0,
                    "hits": 0,
                    "total": 0,
                    "results": [],
                }
        return out

    @staticmethod
    def get_opponent_analysis(
        db: Session,
        player_id: int,
        opponent_team_id: int,
        season: str,
    ) -> Optional[Dict[str, Any]]:
        row = (
            db.query(PlayerOpponentAnalysis)
            .filter_by(
                player_id=player_id,
                opponent_team_id=opponent_team_id,
                season=season,
            )
            .first()
        )
        if not row:
            return None

        pos_def = None
        if row.position and any(
            v is not None
            for v in (
                row.pos_def_rank_pts,
                row.pos_def_rank_reb,
                row.pos_def_rank_ast,
                row.pos_def_rank_3pm,
            )
        ):
            pos_def = {
                "position": row.position,
                "rank_pts": row.pos_def_rank_pts,
                "rank_reb": row.pos_def_rank_reb,
                "rank_ast": row.pos_def_rank_ast,
                "rank_3pm": row.pos_def_rank_3pm,
            }

        matchup_advantage: Dict[str, Any] = {}
        for key, val in (
            ("pts", row.matchup_adv_pts),
            ("reb", row.matchup_adv_reb),
            ("ast", row.matchup_adv_ast),
            ("3pm", row.matchup_adv_3pm),
        ):
            if val is not None:
                matchup_advantage[key] = val

        return {
            "player_id": row.player_id,
            "game_date": row.game_date.isoformat() if row.game_date else None,
            "opponent_team_id": row.opponent_team_id,
            "opponent_team_abbr": row.opponent_team_abbr,
            "is_home_game": row.is_home_game,
            "rest_days": row.rest_days,
            "is_injured": row.is_injured,
            "injury_status": row.injury_status,
            "injury_description": row.injury_description,
            "h2h": {
                "avg_pts": row.h2h_avg_pts,
                "avg_reb": row.h2h_avg_reb,
                "avg_ast": row.h2h_avg_ast,
                "games_played": row.h2h_games_played or 0,
            },
            "opponent_defense": {
                "rank_pts": row.def_rank_pts,
                "rank_reb": row.def_rank_reb,
                "rank_ast": row.def_rank_ast,
                "rank_3pm": row.def_rank_3pm,
            },
            "opponent_defense_vs_position": pos_def,
            "opponent_offense": {
                "rank_pts": row.off_rank_pts,
                "rank_reb": row.off_rank_reb,
                "rank_ast": row.off_rank_ast,
                "rank_3pm": row.off_rank_3pm,
            },
            "matchup_advantage": matchup_advantage,
            "team_performance": {
                "win_rate": row.team_win_rate,
                "conference_rank": row.team_conference_rank,
                "recent_form": row.team_recent_form,
            },
            "opponent_performance": {
                "win_rate": row.opponent_win_rate,
                "conference_rank": row.opponent_conference_rank,
            },
            "formula_version": row.formula_version,
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
            "source": "player_opponent_analysis",
        }

    @staticmethod
    def count_prop_evaluations(db: Session, game_date: date) -> int:
        return (
            db.query(PlayerPropEvaluation)
            .filter(PlayerPropEvaluation.game_date == game_date)
            .count()
        )

    @staticmethod
    def list_prop_evaluations(
        db: Session,
        game_date: date,
        *,
        min_confidence: Optional[float] = None,
        hot_form_only: bool = False,
        limit: int = 100,
        tier_min: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = db.query(PlayerPropEvaluation).filter(PlayerPropEvaluation.game_date == game_date)
        if min_confidence is not None:
            q = q.filter(PlayerPropEvaluation.confidence >= min_confidence)
        if hot_form_only:
            q = q.filter(PlayerPropEvaluation.is_hot.is_(True))
        rows = q.order_by(PlayerPropEvaluation.confidence.desc()).limit(max(limit * 3, limit)).all()

        items: List[Dict[str, Any]] = []
        for r in rows:
            stats = {}
            if r.stats_json:
                try:
                    stats = json.loads(r.stats_json)
                except (TypeError, ValueError):
                    stats = {}
            items.append(
                {
                    "type": r.display_type or (r.stat_type or "").upper(),
                    "playerId": r.player_id,
                    "playerName": r.player_name,
                    "fairLine": r.fair_line if r.fair_line is not None else r.line,
                    "marketLine": r.market_line if r.market_line is not None else r.line,
                    "confidence": r.confidence,
                    "suggestion": r.suggestion or r.direction,
                    "rationale": r.rationale or "",
                    "stats": stats,
                    "gameDate": r.game_date.isoformat() if r.game_date else None,
                    "isHot": bool(r.is_hot),
                    "tier": r.tier,
                    "confidenceSource": r.confidence_source,
                    "rationaleSource": r.rationale_source,
                    "mlAvailable": r.ml_available,
                }
            )
        return items[:limit]
