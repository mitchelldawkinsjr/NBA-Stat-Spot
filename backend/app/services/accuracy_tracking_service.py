"""
Accuracy Tracking Service - Record and settle game predictions and AI pick-of-the-day for historical accuracy.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import structlog

from ..database import get_db
from ..models.prediction_accuracy import GamePredictionRecord, PickOfTheDayRecord
from .nba_api_service import NBADataService

logger = structlog.get_logger()

# Map API stat type to game log key
STAT_TO_GAME_LOG_KEY = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm"}


def _get_db() -> Session:
    return next(get_db())


def record_game_predictions(target_date: date, predictions: List[Dict[str, Any]]) -> int:
    """
    Insert game prediction records for a date (idempotent: skips if records already exist for that date).
    Call this when we cache game_predictions for the day.
    Returns count of new records inserted.
    """
    if not predictions:
        return 0
    db = _get_db()
    try:
        existing = db.query(GamePredictionRecord.id).filter(
            GamePredictionRecord.record_date == target_date
        ).count()
        if existing > 0:
            return 0
        for p in predictions:
            pred_winner = (p.get("predicted_winner") or "").strip().upper()
            home_abbr = (p.get("home") or "").strip().upper()
            win_prob_home = p.get("win_probability_home")
            win_prob_away = p.get("win_probability_away")
            confidence_pct = (
                win_prob_home if pred_winner == home_abbr else win_prob_away
            )
            insight = p.get("key_advantage_summary") or p.get("outlook_summary")
            if insight and len(str(insight)) > 2000:
                insight = str(insight)[:2000]
            r = GamePredictionRecord(
                record_date=target_date,
                game_id=str(p.get("gameId", "")),
                home_abbr=home_abbr,
                away_abbr=(p.get("away") or "").strip().upper(),
                predicted_winner_abbr=pred_winner,
                win_probability_home=win_prob_home,
                win_probability_away=win_prob_away,
                confidence_pct=confidence_pct,
                insight_summary=insight,
            )
            db.add(r)
        db.commit()
        return len(predictions)
    except Exception as e:
        db.rollback()
        logger.warning("record_game_predictions failed", date=target_date.isoformat(), error=str(e))
        return 0
    finally:
        db.close()


def record_pick_of_the_day(target_date: date, pick: Dict[str, Any]) -> bool:
    """
    Insert one pick-of-the-day record (idempotent: skip if record exists for that date).
    Call when we set pick_of_the_day in cache.
    """
    if not pick or pick.get("playerId") is None:
        return False
    db = _get_db()
    try:
        exists = db.query(PickOfTheDayRecord.id).filter(
            PickOfTheDayRecord.record_date == target_date
        ).first()
        if exists:
            return False
        line = pick.get("marketLine") or pick.get("fairLine")
        if line is None:
            return False
        try:
            line_value = float(line)
        except (TypeError, ValueError):
            return False
        stat_type = (pick.get("type") or "PTS").upper().strip()
        if stat_type not in STAT_TO_GAME_LOG_KEY:
            stat_type = "PTS"
        suggestion = (pick.get("suggestion") or "over").lower().strip()
        if suggestion not in ("over", "under"):
            suggestion = "over"
        r = PickOfTheDayRecord(
            record_date=target_date,
            player_id=int(pick["playerId"]),
            player_name=(pick.get("playerName") or "Unknown")[:128],
            stat_type=stat_type,
            line_value=line_value,
            suggestion=suggestion,
            confidence=pick.get("confidence"),
        )
        db.add(r)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.warning("record_pick_of_the_day failed", date=target_date.isoformat(), error=str(e))
        return False
    finally:
        db.close()


def settle_game_predictions(target_date: date) -> Dict[str, Any]:
    """
    For a given date, fetch completed game scores from ESPN and update records with actual_winner and correct.
    Returns { settled: int, not_found: int, errors: list }.
    """
    from .espn_api_service import get_espn_service
    espn = get_espn_service()
    date_str = target_date.strftime("%Y%m%d")
    scoreboard = espn.get_scoreboard(date=date_str)
    if not scoreboard or not isinstance(scoreboard.get("events"), list):
        return {"settled": 0, "not_found": 0, "errors": ["No scoreboard for date"]}
    # Build game_id -> (home_abbr, away_abbr, home_score, away_score, winner_abbr)
    game_results = {}
    for event in scoreboard["events"]:
        game_id = str(event.get("id", ""))
        comps = event.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors") or []
        ev_home = ev_away = None
        for c in competitors:
            abbr = ((c.get("team") or {}).get("abbreviation") or "").strip().upper()
            ha = (c.get("homeAway") or "").lower()
            try:
                score = int(str(c.get("score") or "0").split(".")[0])
            except Exception:
                score = 0
            if ha == "home":
                ev_home = {"abbr": abbr, "score": score}
            else:
                ev_away = {"abbr": abbr, "score": score}
        if not ev_home or not ev_away or (ev_home["score"] == 0 and ev_away["score"] == 0):
            continue
        winner = ev_home["abbr"] if ev_home["score"] > ev_away["score"] else ev_away["abbr"]
        game_results[game_id] = {
            "home_abbr": ev_home["abbr"],
            "away_abbr": ev_away["abbr"],
            "home_score": ev_home["score"],
            "away_score": ev_away["score"],
            "actual_winner_abbr": winner,
        }
    db = _get_db()
    settled = 0
    not_found = 0
    errors = []
    try:
        records = db.query(GamePredictionRecord).filter(
            GamePredictionRecord.record_date == target_date,
            GamePredictionRecord.actual_winner_abbr.is_(None),
        ).all()
        for r in records:
            res = game_results.get(r.game_id)
            if not res:
                not_found += 1
                continue
            r.actual_winner_abbr = res["actual_winner_abbr"]
            r.home_score = res["home_score"]
            r.away_score = res["away_score"]
            r.correct = r.predicted_winner_abbr == res["actual_winner_abbr"]
            r.settled_at = datetime.utcnow()
            settled += 1
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(str(e))
        logger.warning("settle_game_predictions failed", date=target_date.isoformat(), error=str(e))
    finally:
        db.close()
    return {"settled": settled, "not_found": not_found, "errors": errors}


def settle_pick_of_the_day(target_date: date, season: Optional[str] = None) -> Dict[str, Any]:
    """
    For a given date, get the pick record, fetch that player's game log, find the game on that date,
    and set actual_value and hit. Returns { settled: bool, actual_value, hit, push, error }.
    """
    season = season or "2025-26"
    db = _get_db()
    try:
        record = db.query(PickOfTheDayRecord).filter(
            PickOfTheDayRecord.record_date == target_date,
            PickOfTheDayRecord.actual_value.is_(None),
        ).first()
        if not record:
            return {"settled": False, "reason": "no_unsettled_record"}
        logs = NBADataService.fetch_player_game_log(record.player_id, season)
        date_str = target_date.isoformat()
        game_log_key = STAT_TO_GAME_LOG_KEY.get(record.stat_type, "pts")
        actual_value = None
        for g in logs:
            gd = (g.get("game_date") or g.get("GAME_DATE") or "")[:10]
            if gd == date_str:
                raw = g.get(game_log_key) or g.get(game_log_key.upper())
                if raw is not None:
                    try:
                        actual_value = float(raw)
                    except (TypeError, ValueError):
                        pass
                break
        if actual_value is None:
            db.close()
            return {"settled": False, "reason": "game_not_in_log", "player_id": record.player_id}
        record.actual_value = actual_value
        record.settled_at = datetime.utcnow()
        line = record.line_value
        if actual_value == line:
            record.push = True
            record.hit = None  # push
        else:
            record.push = False
            if record.suggestion == "over":
                record.hit = actual_value > line
            else:
                record.hit = actual_value < line
        db.commit()
        return {
            "settled": True,
            "actual_value": actual_value,
            "hit": record.hit,
            "push": record.push,
            "player_name": record.player_name,
            "stat_type": record.stat_type,
            "line_value": record.line_value,
            "suggestion": record.suggestion,
        }
    except Exception as e:
        db.rollback()
        logger.warning("settle_pick_of_the_day failed", date=target_date.isoformat(), error=str(e))
        return {"settled": False, "error": str(e)}
    finally:
        db.close()


def settle_all_for_date(target_date: date, season: Optional[str] = None) -> Dict[str, Any]:
    """Run both game prediction settlement and pick-of-the-day settlement for a date."""
    game_result = settle_game_predictions(target_date)
    pick_result = settle_pick_of_the_day(target_date, season=season)
    return {
        "date": target_date.isoformat(),
        "game_predictions": game_result,
        "pick_of_the_day": pick_result,
    }


def get_accuracy_history(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    limit_days: int = 90,
) -> Dict[str, Any]:
    """
    Return historical accuracy for game predictions and pick of the day.
    """
    to_date = to_date or date.today()
    from_date = from_date or (to_date - timedelta(days=limit_days))
    db = _get_db()
    try:
        # Game predictions: all records in range (settled + pending)
        game_q = db.query(GamePredictionRecord).filter(
            GamePredictionRecord.record_date >= from_date,
            GamePredictionRecord.record_date <= to_date,
        ).order_by(GamePredictionRecord.record_date.desc(), GamePredictionRecord.id)
        game_all = game_q.all()
        game_settled = [r for r in game_all if r.actual_winner_abbr is not None]
        game_correct = sum(1 for r in game_settled if r.correct)
        game_incorrect = sum(1 for r in game_settled if r.correct is False)
        game_pending = sum(1 for r in game_all if r.actual_winner_abbr is None)
        game_total_settled = len(game_settled)
        game_total_all = len(game_all)
        game_pct = round(100.0 * game_correct / game_total_settled, 1) if game_total_settled else None

        # Pick of the day: only settled (exclude push for hit rate)
        pick_q = db.query(PickOfTheDayRecord).filter(
            PickOfTheDayRecord.record_date >= from_date,
            PickOfTheDayRecord.record_date <= to_date,
            PickOfTheDayRecord.actual_value.isnot(None),
        ).order_by(PickOfTheDayRecord.record_date.desc())
        pick_records = pick_q.all()
        pick_hits = sum(1 for r in pick_records if r.hit is True)
        pick_push = sum(1 for r in pick_records if r.push)
        pick_miss = sum(1 for r in pick_records if r.hit is False)
        pick_total = len(pick_records)
        pick_hit_rate = round(100.0 * pick_hits / (pick_total - pick_push), 1) if (pick_total - pick_push) > 0 else None

        # Per-record list for UI (all records, with status)
        game_by_date = []
        for r in game_all:
            status = "graded" if r.actual_winner_abbr is not None else "pending"
            game_by_date.append({
                "date": r.record_date.isoformat(),
                "game_id": r.game_id,
                "matchup": f"{r.away_abbr} @ {r.home_abbr}",
                "predicted_winner": r.predicted_winner_abbr,
                "actual_winner": r.actual_winner_abbr,
                "home_score": r.home_score,
                "away_score": r.away_score,
                "correct": r.correct,
                "status": status,
                "confidence_pct": r.confidence_pct,
                "insight_summary": r.insight_summary,
            })
        pick_by_date = []
        for r in pick_records:
            pick_by_date.append({
                "date": r.record_date.isoformat(),
                "player_name": r.player_name,
                "stat_type": r.stat_type,
                "line_value": r.line_value,
                "suggestion": r.suggestion,
                "actual_value": r.actual_value,
                "hit": r.hit,
                "push": r.push,
                "confidence": r.confidence,
            })
        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "game_predictions": {
                "total": game_total_all,
                "total_settled": game_total_settled,
                "correct": game_correct,
                "incorrect": game_incorrect,
                "pending": game_pending,
                "accuracy_pct": game_pct,
                "records": game_by_date,
            },
            "pick_of_the_day": {
                "total": pick_total,
                "hits": pick_hits,
                "misses": pick_miss,
                "pushes": pick_push,
                "hit_rate_pct": pick_hit_rate,
                "records": pick_by_date,
            },
        }
    finally:
        db.close()
