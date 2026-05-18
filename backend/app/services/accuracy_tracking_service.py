"""
Accuracy Tracking Service - Record and settle game predictions and AI pick-of-the-day for historical accuracy.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session
import structlog

from ..database import get_db
from ..models.prediction_accuracy import GamePredictionRecord, PickOfTheDayRecord, PropPredictionRecord
from ..utils.season import get_current_season, get_previous_season
from .nba_api_service import NBADataService

logger = structlog.get_logger()

# Map API stat type to game log key (aligned with best_picks_service / PropBetEngine)
STAT_TO_GAME_LOG_KEY = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm"}
# Top picks may include PRA; actuals come from pts+reb+ast on the game log row
ALLOWED_PROP_STAT_TYPES = frozenset({"PTS", "REB", "AST", "3PM", "PRA"})

# Confidence tiers — same thresholds as BestPicksService (TIER_LOCK / TIER_STRONG)
TIER_LOCK_THRESHOLD = 78
TIER_STRONG_THRESHOLD = 62


def _confidence_to_tier(confidence: Optional[float]) -> str:
    if confidence is None:
        return "lean"
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return "lean"
    if c >= TIER_LOCK_THRESHOLD:
        return "lock"
    if c >= TIER_STRONG_THRESHOLD:
        return "strong"
    return "lean"


def _confidence_to_band(confidence: Optional[float]) -> str:
    if confidence is None:
        return "unknown"
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return "unknown"
    if c >= 95:
        return "95-100"
    if c >= 90:
        return "90-94"
    if c >= 85:
        return "85-89"
    if c >= 80:
        return "80-84"
    if c >= 75:
        return "75-79"
    if c >= 70:
        return "70-74"
    if c >= 65:
        return "65-69"
    return "<65"




def _season_candidates_for_settlement(target_date: date, season: Optional[str]) -> List[str]:
    """Return one or two seasons to check when settling a dated record."""
    if season:
        return [season]
    primary = f"{target_date.year if target_date.month >= 10 else target_date.year - 1}-{((target_date.year if target_date.month >= 10 else target_date.year - 1) + 1) % 100:02d}"
    candidates = [primary]
    prev = get_previous_season(primary)
    if prev:
        candidates.append(prev)
    current = get_current_season()
    if current not in candidates:
        candidates.append(current)
    return candidates

def _new_prop_bucket() -> Dict[str, int]:
    return {"hits": 0, "misses": 0, "pushes": 0, "settled": 0, "pending": 0}


def _bucket_hit_rate_pct(b: Dict[str, int]) -> Optional[float]:
    graded = b["hits"] + b["misses"]
    if graded <= 0:
        return None
    return round(100.0 * b["hits"] / graded, 1)


def _finalize_bucket(b: Dict[str, int]) -> Dict[str, Any]:
    return {
        "hits": b["hits"],
        "misses": b["misses"],
        "pushes": b["pushes"],
        "settled": b["settled"],
        "pending": b["pending"],
        "hit_rate_pct": _bucket_hit_rate_pct(b),
        "graded_non_push": b["hits"] + b["misses"],
    }


def _prop_outcome(
    actual_value: Optional[float], line_value: float, direction: str
) -> Tuple[str, Optional[bool], bool]:
    """Return (status, hit_or_none_if_push, push)."""
    if actual_value is None:
        return "pending", None, False
    try:
        a = float(actual_value)
        line = float(line_value)
    except (TypeError, ValueError):
        return "pending", None, False
    d = (direction or "over").lower().strip()
    if d not in ("over", "under"):
        d = "over"
    if a == line:
        return "graded", None, True
    if d == "over":
        return "graded", a > line, False
    return "graded", a < line, False


def _actual_from_game_row(stat_type: str, g: Dict[str, Any]) -> Optional[float]:
    st = (stat_type or "PTS").upper().strip()
    if st == "PRA":
        try:
            return (
                float(g.get("pts") or 0)
                + float(g.get("reb") or 0)
                + float(g.get("ast") or 0)
            )
        except (TypeError, ValueError):
            return None
    key = STAT_TO_GAME_LOG_KEY.get(st, "pts")
    raw = g.get(key)
    if raw is None and key:
        raw = g.get(key.upper())
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _aggregate_prop_records(prop_rows: List[PropPredictionRecord]) -> Dict[str, Any]:
    """Build summary + breakdown dicts from prop rows (DB models)."""
    overall = _new_prop_bucket()
    by_tier: Dict[str, Dict[str, int]] = defaultdict(_new_prop_bucket)
    by_band: Dict[str, Dict[str, int]] = defaultdict(_new_prop_bucket)
    by_stat: Dict[str, Dict[str, int]] = defaultdict(_new_prop_bucket)
    by_direction: Dict[str, Dict[str, int]] = defaultdict(_new_prop_bucket)
    tier_stat: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(_new_prop_bucket)
    )
    tier_direction: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(_new_prop_bucket)
    )

    for r in prop_rows:
        tier = _confidence_to_tier(r.confidence)
        band = _confidence_to_band(r.confidence)
        st_key = (r.stat_type or "PTS").upper().strip()
        dir_key = (r.direction or "over").lower().strip()
        if dir_key not in ("over", "under"):
            dir_key = "over"

        status, hit, push = _prop_outcome(r.actual_value, r.line_value, r.direction or "over")
        if status == "pending":
            overall["pending"] += 1
            for m in (by_tier[tier], by_band[band], by_stat[st_key], by_direction[dir_key]):
                m["pending"] += 1
            tier_stat[tier][st_key]["pending"] += 1
            tier_direction[tier][dir_key]["pending"] += 1
            continue

        overall["settled"] += 1
        if push:
            overall["pushes"] += 1
        elif hit:
            overall["hits"] += 1
        else:
            overall["misses"] += 1

        def _add(b: Dict[str, int]) -> None:
            b["settled"] += 1
            if push:
                b["pushes"] += 1
            elif hit:
                b["hits"] += 1
            else:
                b["misses"] += 1

        _add(by_tier[tier])
        _add(by_band[band])
        _add(by_stat[st_key])
        _add(by_direction[dir_key])
        _add(tier_stat[tier][st_key])
        _add(tier_direction[tier][dir_key])

    non_push = overall["hits"] + overall["misses"]
    overall_hit_rate = round(100.0 * overall["hits"] / non_push, 1) if non_push > 0 else None

    lock_b = by_tier.get("lock", _new_prop_bucket())
    lock_non_push = lock_b["hits"] + lock_b["misses"]
    lock_hit_rate_pct = round(100.0 * lock_b["hits"] / lock_non_push, 1) if lock_non_push > 0 else None

    def _finalize_nested(
        d: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, Any]]:
        return {k: _finalize_bucket(v) for k, v in sorted(d.items())}

    def _finalize_tier_nested(
        d: Dict[str, Dict[str, Dict[str, int]]]
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        out: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for tier_k in sorted(d.keys()):
            out[tier_k] = {sk: _finalize_bucket(bv) for sk, bv in sorted(d[tier_k].items())}
        return out

    return {
        "overall": {
            **_finalize_bucket(overall),
            "total": len(prop_rows),
            "hit_rate_pct": overall_hit_rate,
            "lock_hit_rate_pct": lock_hit_rate_pct,
        },
        "by_tier": _finalize_nested(dict(by_tier)),
        "by_confidence_band": _finalize_nested(dict(by_band)),
        "by_stat": _finalize_nested(dict(by_stat)),
        "by_direction": _finalize_nested(dict(by_direction)),
        "tier_x_stat": _finalize_tier_nested(dict(tier_stat)),
        "tier_x_direction": _finalize_tier_nested(dict(tier_direction)),
    }


def _normalize_game_log_date_iso(raw: Union[str, None]) -> str:
    """Normalize NBA game log date to YYYY-MM-DD for comparison with record_date."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00").split("T")[0]).date().isoformat()
    except (ValueError, TypeError):
        pass
    return s[:10] if len(s) >= 10 else s


def _find_game_log_row_for_record_date(logs: List[Dict[str, Any]], target_date: date) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Match a game log row for a record date.
    Prefers exact date, then allows ±1 day to tolerate ET/UTC boundary drift.
    Returns (row, reason).
    """
    if not logs:
        return None, "missing_stats"

    target_iso = target_date.isoformat()
    normalized: List[Tuple[Dict[str, Any], str]] = []
    for g in logs:
        gd = _normalize_game_log_date_iso(g.get("game_date") or g.get("GAME_DATE"))
        if gd:
            normalized.append((g, gd))

    for g, gd in normalized:
        if gd == target_iso:
            return g, "exact_date_match"

    for day_offset in (-1, 1):
        alt_iso = (target_date + timedelta(days=day_offset)).isoformat()
        for g, gd in normalized:
            if gd == alt_iso:
                return g, f"date_offset_{day_offset:+d}"

    return None, "game_not_finished_or_not_in_log"


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
    Call when we set pick_of_the_day in cache (admin warm or public pick-of-the-day endpoint).
    """
    pid = pick.get("playerId") if pick else None
    if pid is None and pick:
        pid = pick.get("player_id")
    if not pick or pid is None:
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
            player_id=int(pid),
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


def settle_pick_of_the_day(
    target_date: date,
    season: Optional[str] = None,
    stats_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    For a given date, get the pick record, fetch that player's game log, find the game on that date,
    and set actual_value and hit. Returns { settled: bool, actual_value, hit, push, error }.
    """
    from .stats_provider import get_settlement_stats_provider

    provider = stats_provider or get_settlement_stats_provider()
    season_candidates = _season_candidates_for_settlement(target_date, season)
    db = _get_db()
    try:
        record = db.query(PickOfTheDayRecord).filter(
            PickOfTheDayRecord.record_date == target_date,
            PickOfTheDayRecord.actual_value.is_(None),
        ).first()
        if not record:
            return {"settled": False, "reason": "no_unsettled_record"}
        logs = []
        for season_try in season_candidates:
            logs = provider.fetch_player_game_log(record.player_id, season_try)
            if logs:
                break
        logger.info("prediction_found", prediction_type="pick_of_the_day", player_id=record.player_id, date=target_date.isoformat())
        game_log_key = STAT_TO_GAME_LOG_KEY.get(record.stat_type, "pts")
        matched_row, match_reason = _find_game_log_row_for_record_date(logs or [], target_date)
        actual_value = None
        if matched_row is not None:
            raw = matched_row.get(game_log_key) or matched_row.get(game_log_key.upper())
            if raw is not None:
                try:
                    actual_value = float(raw)
                except (TypeError, ValueError):
                    pass
        if actual_value is None:
            logger.info("prediction_skipped", prediction_type="pick_of_the_day", player_id=record.player_id, date=target_date.isoformat(), reason=match_reason)
            return {"settled": False, "reason": match_reason, "player_id": record.player_id}
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
        logger.info("settlement_completed", prediction_type="pick_of_the_day", player_id=record.player_id, date=target_date.isoformat(), match_reason=match_reason)
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
        logger.warning("settlement_failed", prediction_type="pick_of_the_day", date=target_date.isoformat(), error=str(e))
        logger.warning("settle_pick_of_the_day failed", date=target_date.isoformat(), error=str(e))
        return {"settled": False, "error": str(e)}
    finally:
        db.close()


def settle_top_picks_for_date(
    target_date: date,
    season: Optional[str] = None,
    stats_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Settle all Top Picks (prop_prediction_records) for a date using player game logs.
    Returns { settled, not_found, errors, not_found_sample }.
    """
    from .stats_provider import get_settlement_stats_provider

    provider = stats_provider or get_settlement_stats_provider()
    season_candidates = _season_candidates_for_settlement(target_date, season)
    db = _get_db()
    settled = 0
    not_found = 0
    errors: List[str] = []
    not_found_sample: List[Dict[str, Any]] = []
    try:
        records = (
            db.query(PropPredictionRecord)
            .filter(
                PropPredictionRecord.record_date == target_date,
                PropPredictionRecord.actual_value.is_(None),
            )
            .all()
        )
        for record in records:
            logger.info("prediction_found", prediction_type="top_pick", player_id=record.player_id, date=target_date.isoformat())
            try:
                logs = []
                for season_try in season_candidates:
                    logs = provider.fetch_player_game_log(record.player_id, season_try)
                    if logs:
                        break
            except Exception as e:
                errors.append(f"player {record.player_id}: {e}")
                continue
            matched_row, match_reason = _find_game_log_row_for_record_date(logs or [], target_date)
            actual_value: Optional[float] = _actual_from_game_row(record.stat_type, matched_row) if matched_row else None
            if actual_value is None:
                not_found += 1
                reason = match_reason if record.stat_type in ALLOWED_PROP_STAT_TYPES else "unsupported_type"
                logger.info("prediction_skipped", prediction_type="top_pick", player_id=record.player_id, date=target_date.isoformat(), reason=reason)
                if len(not_found_sample) < 40:
                    not_found_sample.append(
                        {
                            "player_id": record.player_id,
                            "player_name": record.player_name,
                            "stat_type": record.stat_type,
                            "reason": reason,
                        }
                    )
                continue
            record.actual_value = actual_value
            pred = record.predicted_value if record.predicted_value is not None else record.line_value
            try:
                record.error = float(actual_value) - float(pred) if pred is not None else None
            except (TypeError, ValueError):
                record.error = None
            record.settled_at = datetime.utcnow()
            settled += 1
            logger.info("settlement_completed", prediction_type="top_pick", player_id=record.player_id, date=target_date.isoformat(), match_reason=match_reason)
        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(str(e))
        logger.warning("settlement_failed", prediction_type="top_picks", date=target_date.isoformat(), error=str(e))
        logger.warning("settle_top_picks_for_date failed", date=target_date.isoformat(), error=str(e))
    finally:
        db.close()
    return {
        "settled": settled,
        "not_found": not_found,
        "errors": errors,
        "not_found_sample": not_found_sample,
    }


def settle_all_for_date(
    target_date: date,
    season: Optional[str] = None,
    stats_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run game predictions, pick-of-the-day, and Top Picks (prop) settlement for a date."""
    from .stats_provider import get_settlement_stats_provider

    provider = stats_provider or get_settlement_stats_provider()
    game_result = settle_game_predictions(target_date)
    pick_result = settle_pick_of_the_day(target_date, season=season, stats_provider=provider)
    top_picks_result = settle_top_picks_for_date(target_date, season=season, stats_provider=provider)
    return {
        "date": target_date.isoformat(),
        "game_predictions": game_result,
        "pick_of_the_day": pick_result,
        "top_picks": top_picks_result,
    }


def record_prop_predictions(target_date: date, picks: List[Dict[str, Any]], model_version: Optional[str] = None) -> int:
    """
    Insert prop prediction records for a date (from get_top_picks or daily props).
    Returns count of records inserted.
    """
    if not picks:
        return 0
    try:
        date_obj = target_date if isinstance(target_date, date) else date.fromisoformat(str(target_date)[:10])
    except (ValueError, TypeError):
        return 0
    db = _get_db()
    inserted = 0
    try:
        # One batch per calendar day — avoid duplicate rows on repeated cache refreshes
        if (
            db.query(PropPredictionRecord.id)
            .filter(PropPredictionRecord.record_date == date_obj)
            .first()
        ):
            return 0
        for p in picks:
            player_id = p.get("playerId") or p.get("player_id")
            if player_id is None:
                continue
            stat_type = (p.get("type") or "PTS").upper().strip()
            if stat_type not in ALLOWED_PROP_STAT_TYPES:
                continue
            line_val = p.get("marketLine") or p.get("fairLine")
            if line_val is None:
                continue
            try:
                line_value = float(line_val)
            except (TypeError, ValueError):
                continue
            direction = (p.get("suggestion") or "over").lower().strip()
            if direction not in ("over", "under"):
                direction = "over"
            confidence = p.get("confidence")
            try:
                confidence = float(confidence) if confidence is not None else None
            except (TypeError, ValueError):
                confidence = None
            r = PropPredictionRecord(
                record_date=date_obj,
                player_id=int(player_id),
                player_name=(p.get("playerName") or p.get("player_name") or "")[:128],
                stat_type=stat_type,
                line_value=line_value,
                direction=direction,
                confidence=confidence,
                predicted_value=line_value,
                model_version=model_version,
            )
            db.add(r)
            inserted += 1
        db.commit()
        return inserted
    except Exception as e:
        db.rollback()
        logger.warning("record_prop_predictions failed", date=str(target_date), error=str(e))
        return 0
    finally:
        db.close()


def settle_open_predictions(
    target_date: date,
    season: Optional[str] = None,
    stats_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Settle all open (unsettled) prediction records up to a target date.
    Fetches finalized game stats, compares to stored lines, writes actual_value and hit.
    Intended to be called nightly after games complete (e.g. via cron).
    """
    db = _get_db()
    try:
        dates: set[date] = set()
        dates.update(
            d for (d,) in db.query(GamePredictionRecord.record_date)
            .filter(GamePredictionRecord.record_date <= target_date, GamePredictionRecord.actual_winner_abbr.is_(None))
            .all()
        )
        dates.update(
            d for (d,) in db.query(PickOfTheDayRecord.record_date)
            .filter(PickOfTheDayRecord.record_date <= target_date, PickOfTheDayRecord.actual_value.is_(None))
            .all()
        )
        dates.update(
            d for (d,) in db.query(PropPredictionRecord.record_date)
            .filter(PropPredictionRecord.record_date <= target_date, PropPredictionRecord.actual_value.is_(None))
            .all()
        )
    finally:
        db.close()

    ordered_dates = sorted(dates)
    results = [
        settle_all_for_date(d, season=season, stats_provider=stats_provider) for d in ordered_dates
    ]
    return {
        "target_date": target_date.isoformat(),
        "dates_processed": [d.isoformat() for d in ordered_dates],
        "count_dates": len(ordered_dates),
        "results": results,
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

        # Pick of the day: all rows in range for history table; settled subset for rates
        pick_all = (
            db.query(PickOfTheDayRecord)
            .filter(
                PickOfTheDayRecord.record_date >= from_date,
                PickOfTheDayRecord.record_date <= to_date,
            )
            .order_by(PickOfTheDayRecord.record_date.desc())
            .all()
        )
        pick_settled = [r for r in pick_all if r.actual_value is not None]
        pick_pending_count = len(pick_all) - len(pick_settled)
        pick_hits = sum(1 for r in pick_settled if r.hit is True)
        pick_push = sum(1 for r in pick_settled if r.push)
        pick_miss = sum(1 for r in pick_settled if r.hit is False)
        pick_settled_count = len(pick_settled)
        pick_non_push = pick_settled_count - pick_push
        pick_hit_rate = round(100.0 * pick_hits / pick_non_push, 1) if pick_non_push > 0 else None

        # MAE and RMSE for pick-of-the-day (exclude pushes)
        pick_errors = []
        for r in pick_settled:
            if r.actual_value is not None and not r.push:
                pick_errors.append(abs(float(r.actual_value) - float(r.line_value)))
        pick_mae = round(sum(pick_errors) / len(pick_errors), 2) if pick_errors else None
        pick_rmse = round((sum(e * e for e in pick_errors) / len(pick_errors)) ** 0.5, 2) if pick_errors else None

        # Combined: settled game winners + settled AI picks (non-push), one point each
        combined_total = game_total_settled + pick_non_push
        combined_correct = game_correct + pick_hits
        combined_accuracy_pct = (
            round(100.0 * combined_correct / combined_total, 1) if combined_total > 0 else None
        )

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
        for r in pick_all:
            p_status = "graded" if r.actual_value is not None else "pending"
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
                "status": p_status,
            })

        prop_all = (
            db.query(PropPredictionRecord)
            .filter(
                PropPredictionRecord.record_date >= from_date,
                PropPredictionRecord.record_date <= to_date,
            )
            .order_by(PropPredictionRecord.record_date.desc(), PropPredictionRecord.id)
            .all()
        )
        top_picks_summary = _aggregate_prop_records(prop_all)
        top_picks_records: List[Dict[str, Any]] = []
        for r in prop_all:
            status, hit, push = _prop_outcome(r.actual_value, r.line_value, r.direction or "over")
            top_picks_records.append({
                "id": r.id,
                "date": r.record_date.isoformat(),
                "player_id": r.player_id,
                "player_name": r.player_name or "",
                "stat_type": r.stat_type,
                "direction": r.direction,
                "line_value": r.line_value,
                "confidence": r.confidence,
                "tier": _confidence_to_tier(r.confidence),
                "confidence_band": _confidence_to_band(r.confidence),
                "actual_value": r.actual_value,
                "error": r.error,
                "hit": hit,
                "push": push,
                "status": status,
            })

        model_version = None
        try:
            from ..models.app_settings import AppSettings
            row = db.query(AppSettings).filter(AppSettings.key == "ml_model_version").first()
            if row and row.value:
                model_version = row.value
        except Exception:
            pass

        return {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "model_version": model_version,
            "combined_accuracy": {
                "accuracy_pct": combined_accuracy_pct,
                "correct": combined_correct,
                "total": combined_total,
                "game_settled": game_total_settled,
                "ai_pick_graded_non_push": pick_non_push,
            },
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
                "total": len(pick_all),
                "settled": pick_settled_count,
                "pending": pick_pending_count,
                "hits": pick_hits,
                "misses": pick_miss,
                "pushes": pick_push,
                "hit_rate_pct": pick_hit_rate,
                "mae": pick_mae,
                "rmse": pick_rmse,
                "win_rate": pick_hit_rate,
                "records": pick_by_date,
            },
            "top_picks": {
                **top_picks_summary,
                "records": top_picks_records,
            },
        }
    finally:
        db.close()
