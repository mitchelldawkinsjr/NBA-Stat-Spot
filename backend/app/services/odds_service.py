"""
The Odds API (https://the-odds-api.com/) — fetch NBA player props and game totals,
store in prop_bet_lines, and serve aggregated lines for props UI.
"""
from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict
from datetime import date, datetime, timezone
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from sqlalchemy.orm import Session

from ..models.prop_bet_lines import PropBetLine
from .nba_api_service import NBADataService

logger = structlog.get_logger()

# API bookmaker keys (lowercase, as returned by The Odds API)
TARGET_BOOK_KEYS = ("draftkings", "fanduel", "betmgm", "caesars")

# Markets to request in one call (counts as 1 request toward quota)
PLAYER_MARKETS = (
    "player_points",
    "player_rebounds",
    "player_assists",
    "player_threes",
    "player_points_rebounds_assists",
)
GAME_MARKETS = ("totals",)

MARKET_TO_DISPLAY = {
    "player_points": "PTS",
    "player_rebounds": "REB",
    "player_assists": "AST",
    "player_threes": "3PM",
    "player_points_rebounds_assists": "PRA",
    "totals": "TOTAL",
}

DISPLAY_TO_STAT = {
    "PTS": "pts",
    "REB": "reb",
    "AST": "ast",
    "3PM": "tpm",
    "PRA": "pra",
}


def _american_to_float(price: Any) -> Optional[float]:
    if price is None:
        return None
    try:
        return float(price)
    except (TypeError, ValueError):
        return None


def _parse_commence_date(commence_iso: Optional[str]) -> Optional[date]:
    if not commence_iso:
        return None
    try:
        dt = datetime.fromisoformat(commence_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).date()
    except Exception:
        return None


def _load_player_name_index() -> Tuple[Dict[str, int], List[str]]:
    """Map normalized full name -> player id for fuzzy match."""
    try:
        players = NBADataService.fetch_all_players_including_rookies()
    except Exception as e:
        logger.warning("odds: could not load players", error=str(e))
        return {}, []
    by_lower: Dict[str, int] = {}
    names: List[str] = []
    for p in players:
        fn = (p.get("full_name") or "").strip()
        if not fn:
            continue
        pid = p.get("id")
        if pid is None:
            continue
        by_lower[fn.lower()] = int(pid)
        names.append(fn)
    return by_lower, names


def resolve_player_id(outcome_name: str, by_lower: Dict[str, int], name_list: List[str]) -> Optional[int]:
    """Match Odds API player name to NBA player id."""
    raw = (outcome_name or "").strip()
    if not raw:
        return None
    if raw.lower() in by_lower:
        return by_lower[raw.lower()]
    matches = get_close_matches(raw, name_list, n=1, cutoff=0.82)
    if matches:
        return by_lower.get(matches[0].lower())
    # Last name only fallback (risky) — skip
    return None


def _pair_player_prop_outcomes(outcomes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Group Over/Under pairs by (player name, point). The Odds API uses name=player,
    description=Over|Under for player props.
    """
    buckets: Dict[Tuple[str, float], Dict[str, Any]] = {}
    for o in outcomes:
        name = (o.get("name") or "").strip()
        desc = (o.get("description") or "").strip().lower()
        point = o.get("point")
        price = _american_to_float(o.get("price"))
        if point is None:
            continue
        try:
            pt = float(point)
        except (TypeError, ValueError):
            continue
        # Totals-style: name is Over/Under, no player — skip here (handled in totals)
        if name.lower() in ("over", "under") and not desc:
            continue
        player_key = name
        if desc in ("over", "under"):
            key = (player_key.lower(), pt)
            if key not in buckets:
                buckets[key] = {"name": player_key, "point": pt, "over": None, "under": None}
            if desc == "over":
                buckets[key]["over"] = price
            else:
                buckets[key]["under"] = price
    return [v for v in buckets.values() if v.get("over") is not None or v.get("under") is not None]


def _pair_totals_outcomes(outcomes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    over_p = under_p = None
    line = None
    for o in outcomes:
        name = (o.get("name") or "").strip().lower()
        point = o.get("point")
        price = _american_to_float(o.get("price"))
        if point is not None:
            try:
                line = float(point)
            except (TypeError, ValueError):
                pass
        if name == "over":
            over_p = price
        elif name == "under":
            under_p = price
    if line is None:
        return None
    return {"point": line, "over": over_p, "under": under_p}


def fetch_nba_odds_from_api() -> List[Dict[str, Any]]:
    """Call The Odds API for NBA (player props + totals). Returns events list."""
    api_key = os.environ.get("THE_ODDS_API_KEY", "").strip()
    if not api_key:
        logger.warning("THE_ODDS_API_KEY not set; skipping odds fetch")
        return []

    regions = "us"
    markets = ",".join(PLAYER_MARKETS + GAME_MARKETS)
    url = (
        "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
        f"?regions={regions}&markets={markets}&oddsFormat=american&apiKey={api_key}"
    )
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.get(url)
                r.raise_for_status()
                data = r.json()
                remaining = r.headers.get("x-requests-remaining")
                if remaining is not None:
                    logger.info("odds_api_fetch_ok", requests_remaining=remaining)
                return data if isinstance(data, list) else []
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    logger.warning("odds_api_fetch_failed_after_retries", error=str(last_err) if last_err else "")
    return []


def store_odds_data(db: Session, events: List[Dict[str, Any]]) -> int:
    """
    Parse events and insert PropBetLine rows. Deletes existing rows for the same event ids first.
    Returns number of rows inserted.
    """
    if not events:
        return 0

    event_ids = [e.get("id") for e in events if e.get("id")]
    if not event_ids:
        return 0

    db.query(PropBetLine).filter(PropBetLine.nba_event_id.in_(event_ids)).delete(synchronize_session=False)
    db.commit()

    by_lower, name_list = _load_player_name_index()
    inserted = 0
    now = datetime.now(timezone.utc)

    for ev in events:
        eid = ev.get("id")
        commence = ev.get("commence_time")
        gd = _parse_commence_date(commence)
        cdt = None
        if commence:
            try:
                cdt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            except Exception:
                cdt = None

        for book in ev.get("bookmakers") or []:
            bkey = (book.get("key") or "").lower()
            if bkey not in TARGET_BOOK_KEYS:
                continue
            for market in book.get("markets") or []:
                mkey = market.get("key") or ""
                outcomes = market.get("outcomes") or []

                if mkey == "totals":
                    paired = _pair_totals_outcomes(outcomes)
                    if not paired:
                        continue
                    row = PropBetLine(
                        id=str(uuid.uuid4()),
                        player_id=None,
                        game_date=gd,
                        prop_type="TOTAL",
                        line_value=paired["point"],
                        over_odds=paired.get("over"),
                        under_odds=paired.get("under"),
                        source=bkey,
                        nba_event_id=eid,
                        commence_time=cdt,
                        updated_at=now,
                    )
                    db.add(row)
                    inserted += 1
                    continue

                if mkey not in MARKET_TO_DISPLAY:
                    continue
                disp = MARKET_TO_DISPLAY[mkey]
                for pair in _pair_player_prop_outcomes(outcomes):
                    pname = pair.get("name") or ""
                    pid = resolve_player_id(pname, by_lower, name_list)
                    if pid is None:
                        continue
                    row = PropBetLine(
                        id=str(uuid.uuid4()),
                        player_id=pid,
                        game_date=gd,
                        prop_type=disp,
                        line_value=pair.get("point"),
                        over_odds=pair.get("over"),
                        under_odds=pair.get("under"),
                        source=bkey,
                        nba_event_id=eid,
                        commence_time=cdt,
                        updated_at=now,
                    )
                    db.add(row)
                    inserted += 1

    db.commit()
    return inserted


def sync_nba_odds(db: Session) -> Dict[str, Any]:
    """Fetch from API and store. Safe to call on a schedule."""
    if not (os.environ.get("THE_ODDS_API_KEY") or "").strip():
        return {"events": 0, "rows_inserted": 0, "ok": False, "error": "THE_ODDS_API_KEY not set"}
    events = fetch_nba_odds_from_api()
    n = store_odds_data(db, events)
    return {"events": len(events), "rows_inserted": n, "ok": True}


def get_lines_for_player_game(
    db: Session,
    player_id: int,
    game_date: Optional[date] = None,
) -> Dict[str, float]:
    """
    Latest line_value per prop type (median across books if multiple).
    Used to auto-fill marketLines when API user omits them.
    """
    q = db.query(PropBetLine).filter(PropBetLine.player_id == player_id)
    if game_date:
        q = q.filter(PropBetLine.game_date == game_date)
    rows = q.all()
    if not rows:
        # nearest future/past game date for this player
        q2 = (
            db.query(PropBetLine)
            .filter(PropBetLine.player_id == player_id)
            .order_by(PropBetLine.game_date.desc())
        )
        rows = q2.limit(200).all()

    by_type: Dict[str, List[float]] = defaultdict(list)
    for r in rows:
        if r.prop_type and r.line_value is not None:
            by_type[r.prop_type].append(float(r.line_value))

    out: Dict[str, float] = {}
    for k, vals in by_type.items():
        if not vals:
            continue
        vals.sort()
        mid = vals[len(vals) // 2]
        out[k] = round(mid * 2) / 2.0
    return out


def build_live_odds_payload(
    db: Session,
    player_id: int,
    game_date: Optional[date],
    prop_display: str,
) -> Dict[str, Any]:
    """Structured live odds by book for one prop type."""
    q = db.query(PropBetLine).filter(
        PropBetLine.player_id == player_id,
        PropBetLine.prop_type == prop_display,
    )
    if game_date:
        q = q.filter(PropBetLine.game_date == game_date)
    rows = q.all()
    if not rows and game_date:
        q2 = db.query(PropBetLine).filter(
            PropBetLine.player_id == player_id,
            PropBetLine.prop_type == prop_display,
        )
        rows = q2.order_by(PropBetLine.game_date.desc()).limit(40).all()

    by_book: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        bk = r.source or "unknown"
        by_book[bk] = {
            "line": r.line_value,
            "over": r.over_odds,
            "under": r.under_odds,
        }

    best_over_line: Optional[float] = None
    best_under_line: Optional[float] = None
    for _bk, d in by_book.items():
        ln = d.get("line")
        if ln is None:
            continue
        if best_over_line is None or ln < best_over_line:
            best_over_line = ln
        if best_under_line is None or ln > best_under_line:
            best_under_line = ln

    return {
        "byBook": by_book,
        "bestLine": {"over": best_over_line, "under": best_under_line},
        "source": "the_odds_api",
    }


def get_player_odds_comparison(
    db: Session,
    player_id: int,
    game_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Full comparison for Live Odds UI: all prop types we have in DB."""
    gd: Optional[date] = None
    if game_date:
        try:
            gd = datetime.strptime(game_date, "%Y-%m-%d").date()
        except Exception:
            gd = None

    props = ["PTS", "REB", "AST", "3PM"]
    result: Dict[str, Any] = {"playerId": player_id, "gameDate": game_date, "props": {}}
    for p in props:
        result["props"][p] = build_live_odds_payload(db, player_id, gd, p)
    return result


def get_median_line_for_player_prop(
    db: Session,
    player_id: int,
    prop_type: str,
    game_date: Optional[date],
) -> Optional[float]:
    """Median line across books for one player + prop + optional game date."""
    q = db.query(PropBetLine).filter(
        PropBetLine.player_id == player_id,
        PropBetLine.prop_type == prop_type,
    )
    if game_date:
        q = q.filter(PropBetLine.game_date == game_date)
    rows = q.all()
    if not rows:
        q2 = (
            db.query(PropBetLine)
            .filter(
                PropBetLine.player_id == player_id,
                PropBetLine.prop_type == prop_type,
            )
            .order_by(PropBetLine.game_date.desc())
            .limit(80)
        )
        rows = q2.all()
    vals = sorted([float(r.line_value) for r in rows if r.line_value is not None])
    if not vals:
        return None
    return vals[len(vals) // 2]


def enrich_prop_items_with_live_lines(
    db: Session,
    items: List[Dict[str, Any]],
    game_date_str: Optional[str],
) -> None:
    """Overlay sportsbook line onto marketLine when synced odds exist; preserve fairLine."""
    if not items:
        return
    from datetime import datetime as dt

    gd: Optional[date] = None
    if game_date_str:
        try:
            gd = dt.strptime(game_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    for s in items:
        pid = s.get("playerId")
        typ = s.get("type")
        if pid is None or not typ:
            continue
        if s.get("fairLine") is None and s.get("marketLine") is not None:
            s["fairLine"] = s["marketLine"]
        live = get_median_line_for_player_prop(db, int(pid), str(typ), gd)
        if live is not None:
            s["marketLine"] = float(live)
            s["lineSource"] = "live_odds"


def get_game_totals_for_date(db: Session, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
    """Game total lines (no player) for a slate date."""
    q = db.query(PropBetLine).filter(PropBetLine.prop_type == "TOTAL")
    if target_date:
        q = q.filter(PropBetLine.game_date == target_date)
    rows = q.all()
    by_event: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        eid = r.nba_event_id or ""
        if eid not in by_event:
            by_event[eid] = {"eventId": eid, "gameDate": r.game_date.isoformat() if r.game_date else None, "books": {}}
        bk = r.source or "unknown"
        by_event[eid]["books"][bk] = {
            "line": r.line_value,
            "over": r.over_odds,
            "under": r.under_odds,
        }
    return list(by_event.values())
