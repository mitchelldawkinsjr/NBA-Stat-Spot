import re
from fastapi import APIRouter, Query, Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, timedelta, datetime
import structlog
from ..services.live_game_service import LiveGameService
from ..services.espn_api_service import get_espn_service
from ..services.game_prediction_service import get_game_prediction_service
from ..services.cache_service import get_cache_service
from ..services.llm.prompt_builder import BEST_MATCH_SYSTEM_PROMPT, build_best_match_prompt

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/games", tags=["games_v1"])


def _games_from_espn_scoreboard(target_date: date) -> List[Dict[str, Any]]:
    """Fetch games for a date from ESPN scoreboard and map to our game format (gameId, home, away, gameTimeUTC, gameEt, status)."""
    try:
        espn_service = get_espn_service()
        # ESPN expects YYYYMMDD
        date_str = target_date.strftime("%Y%m%d")
        scoreboard_data = espn_service.get_scoreboard(date=date_str)
        if not scoreboard_data or not isinstance(scoreboard_data.get("events"), list):
            return []
        games = []
        for event in scoreboard_data["events"]:
            try:
                game_id = str(event.get("id", ""))
                event_date = event.get("date") or ""
                status_obj = event.get("status") or {}
                status_id = str(status_obj.get("id", "1"))
                status_desc = (status_obj.get("description") or "").upper()
                if status_id == "3" or "FINAL" in status_desc or status_obj.get("completed"):
                    status = "FINAL"
                elif status_id == "2" or "IN PROGRESS" in status_desc or "LIVE" in status_desc:
                    status = "LIVE"
                else:
                    status = "SCHEDULED"
                home_abbr = None
                away_abbr = None
                comps = event.get("competitions") or []
                if comps:
                    for comp in comps:
                        for c in comp.get("competitors") or []:
                            abbr = (c.get("team") or {}).get("abbreviation", "")
                            if (c.get("homeAway") or "").lower() == "home":
                                home_abbr = abbr
                            else:
                                away_abbr = abbr
                if home_abbr is None and away_abbr is None:
                    continue
                games.append({
                    "gameId": game_id,
                    "home": home_abbr or "",
                    "away": away_abbr or "",
                    "gameTimeUTC": event_date,
                    "gameEt": event_date,
                    "status": status,
                })
            except (KeyError, TypeError, IndexError) as e:
                logger.warning("Skip ESPN event", event_id=event.get("id"), error=str(e))
                continue
        return games
    except Exception as e:
        logger.warning("ESPN scoreboard failed", date=str(target_date), error=str(e))
        return []


@router.get(
    "/today",
    summary="Get games for a specific date",
    description="""
    Get all NBA games scheduled for a specific date.
    Uses ESPN scoreboard (live, reliable). Date format: YYYY-MM-DD
    """,
    response_description="List of games for the specified date",
    tags=["games_v1"]
)
def today(
    date_param: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15", alias="date")
):
    """
    Get today's games. If date is provided (YYYY-MM-DD), use that date.
    Otherwise, use server's current date. Source: ESPN scoreboard only.
    """
    target_date = date.today()
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    games = _games_from_espn_scoreboard(target_date)
    return {"games": games}

@router.get(
    "/upcoming",
    summary="Get upcoming games",
    description="Get upcoming games within the specified number of days. Uses ESPN scoreboard per day.",
    response_description="List of upcoming games",
    tags=["games_v1"]
)
def upcoming(
    days: int = Query(7, description="Number of days ahead to look for games", example=7, ge=1, le=30)
):
    """Get upcoming games for the next N days (ESPN scoreboard per date)."""
    try:
        all_games = []
        today = date.today()
        for day_offset in range(days + 1):
            target_date = today + timedelta(days=day_offset)
            games_for_date = _games_from_espn_scoreboard(target_date)
            for game in games_for_date:
                status = (game.get("status") or "").upper()
                if status not in ("FINAL", "COMPLETED"):
                    all_games.append(game)
        return {"games": all_games}
    except Exception as e:
        logger.error("Failed to fetch upcoming games", days=days, error=str(e))
        return {"games": []}

@router.get(
    "/predictions",
    summary="Get today's game predictions",
    description="Get predicted winner, win probability, and key advantage summary for each game on the given date.",
    response_description="List of game predictions",
    tags=["games_v1"],
)
def get_predictions(
    date_param: Optional[str] = Query(None, description="Date YYYY-MM-DD. Default: today.", alias="date"),
):
    """Return predictions for all games on the given date."""
    target_date = date.today()
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    try:
        svc = get_game_prediction_service()
        predictions = svc.get_todays_predictions(target_date)
        return {"date": target_date.isoformat(), "predictions": predictions}
    except Exception as e:
        logger.error("Failed to fetch game predictions", date=target_date.isoformat(), error=str(e))
        return {"date": target_date.isoformat(), "predictions": [], "error": str(e)}


def _parse_best_match_response(
    llm_text: str, predictions: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Parse LLM response to find matchup (e.g. 'BOS @ MIA' or 'MIA vs BOS') and match to a game.
    Returns the prediction dict for the matched game, or None.
    """
    if not llm_text or not predictions:
        return None
    text = (llm_text or "").upper()
    # Build set of (away, home) and (home, away) for each game (abbrs normalized)
    for p in predictions:
        home = (p.get("home") or "").strip().upper()
        away = (p.get("away") or "").strip().upper()
        if not home or not away:
            continue
        # Look for "AWAY @ HOME" or "HOME vs AWAY" or "AWAY vs HOME"
        if (away + " @ " + home) in text or (home + " @ " + away) in text:
            return p
        if (away + " VS " + home) in text or (home + " VS " + away) in text:
            return p
        if (away + " VS. " + home) in text or (home + " VS. " + away) in text:
            return p
    # Regex: two 3-letter abbrs separated by @ or vs
    abbrs = set()
    for p in predictions:
        abbrs.add((p.get("home") or "").strip().upper())
        abbrs.add((p.get("away") or "").strip().upper())
    # Pattern: WORD @ WORD or WORD vs WORD (WORD = 2-4 chars)
    for m in re.finditer(r"([A-Z]{2,4})\s*(?:@|VS\.?)\s*([A-Z]{2,4})", text, re.IGNORECASE):
        a1, a2 = m.group(1).upper(), m.group(2).upper()
        for p in predictions:
            home = (p.get("home") or "").strip().upper()
            away = (p.get("away") or "").strip().upper()
            if (a1 == away and a2 == home) or (a1 == home and a2 == away):
                return p
    return None


def _extract_insight_and_factors(llm_text: str) -> Tuple[str, List[str]]:
    """Extract WHY and FACTORS from LLM response. Returns (insight_paragraph, key_factors_list)."""
    insight = ""
    factors: List[str] = []
    if not llm_text:
        return insight, factors
    lines = [ln.strip() for ln in llm_text.split("\n") if ln.strip()]
    for i, line in enumerate(lines):
        upper = line.upper()
        if upper.startswith("WHY:") or upper.startswith("INSIGHT:"):
            insight = line.split(":", 1)[-1].strip()
        elif upper.startswith("FACTORS:"):
            rest = line.split(":", 1)[-1].strip()
            factors = [x.strip() for x in rest.split(",") if x.strip()]
    if not insight:
        # Use first 1-2 sentences that don't look like MATCHUP/WHY/FACTORS
        for line in lines:
            if not re.match(r"^(MATCHUP|WHY|FACTORS):", line, re.I):
                insight = line[:400]
                break
    return insight or llm_text[:400], factors


def compute_best_match_of_the_day(target_date: date) -> Optional[Dict[str, Any]]:
    """
    Compute best match of the day (no cache). Used by the endpoint and by admin warm-dashboard.
    Returns the match payload dict or None if no games.
    """
    try:
        svc = get_game_prediction_service()
        predictions = svc.get_todays_predictions(target_date)
    except Exception as e:
        logger.warning("Failed to get predictions for best match", date=target_date.isoformat(), error=str(e))
        predictions = []

    if not predictions:
        return None

    try:
        from ..services.rationale_generator import get_rationale_generator as _gen
        first_svc = (_gen().services or [None])[0]
        for_chat = hasattr(first_svc, "client") if first_svc else True
    except Exception:
        for_chat = True

    prompt = build_best_match_prompt(predictions=predictions, for_chat_api=for_chat)

    insight = ""
    key_factors: List[str] = []
    matched = None
    source = "fallback"

    try:
        from ..services.rationale_generator import get_rationale_generator
        gen = get_rationale_generator()
        if gen.is_available():
            first_svc = gen.services[0] if gen.services else None
            result = None
            if for_chat and first_svc and hasattr(first_svc, "client"):
                try:
                    resp = first_svc.client.chat.completions.create(
                        model=first_svc.model,
                        messages=[
                            {"role": "system", "content": BEST_MATCH_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.4,
                        max_tokens=400,
                    )
                    result = (resp.choices[0].message.content or "").strip()
                except Exception:
                    pass
            if not result:
                result = gen._generate_simple(prompt, max_tokens=400)
            if result:
                matched = _parse_best_match_response(result, predictions)
                insight, key_factors = _extract_insight_and_factors(result)
                if matched:
                    source = "llm"
    except Exception as e:
        logger.debug("Best match LLM failed", error=str(e))

    if not matched:
        def _closeness(p: Dict[str, Any]) -> float:
            wh = p.get("win_probability_home") or 50
            return -abs(wh - 50)
        predictions_sorted = sorted(predictions, key=_closeness)
        matched = predictions_sorted[0] if predictions_sorted else None
        if matched:
            insight = (
                f"{matched.get('predicted_winner')} favored with a close spread. "
                f"Key advantage: {matched.get('key_advantage_summary') or 'balanced matchup'}."
            )
            key_factors = [matched.get("key_advantage_summary")] if matched.get("key_advantage_summary") else []

    if not matched:
        return None

    return {
        "gameId": matched.get("gameId"),
        "home": matched.get("home"),
        "away": matched.get("away"),
        "home_full_name": matched.get("home_full_name"),
        "away_full_name": matched.get("away_full_name"),
        "predicted_winner": matched.get("predicted_winner"),
        "win_probability_home": matched.get("win_probability_home"),
        "win_probability_away": matched.get("win_probability_away"),
        "key_advantage_summary": matched.get("key_advantage_summary"),
        "insight": insight,
        "key_factors": key_factors,
        "source": source,
    }


@router.get(
    "/best-match-of-the-day",
    summary="Get Best Match of the Day",
    description="""
    Returns the single best game of the day based on an LLM analysis of today's predictions.
    Uses game predictions (win probability, key advantage, PPG, pace) to build a prompt;
    the LLM picks one game and provides a short insight and key factors.
    Cached per day (24h TTL). Falls back to most competitive game (closest to 50% win prob) if LLM unavailable.
    """,
    response_description="One game (gameId, home, away, insight, key_factors) or null if no games.",
    tags=["games_v1"],
)
def best_match_of_the_day(
    date_param: Optional[str] = Query(None, description="Target date YYYY-MM-DD. Defaults to today.", alias="date"),
):
    """Best match of the day: LLM picks one game from today's predictions and explains why."""
    target_date = date.today()
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    cache = get_cache_service()
    cache_key = f"best_match_of_the_day:{target_date.isoformat()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return {"match": cached, "cached": True, "date": target_date.isoformat()}

    out = compute_best_match_of_the_day(target_date)
    if out is None:
        cache.set(cache_key, None, ttl=86400)
        return {"match": None, "cached": False, "date": target_date.isoformat()}
    cache.set(cache_key, out, ttl=86400)
    return {"match": out, "cached": False, "date": target_date.isoformat()}


@router.get(
    "/predictions/{game_id}",
    summary="Get game prediction detail",
    description="Get full prediction and outlook for a single game (for game detail page).",
    response_description="Game prediction detail with outlook and comparison stats",
    tags=["games_v1"],
)
def get_prediction_detail(
    game_id: str = Path(..., description="ESPN game ID"),
    date_param: Optional[str] = Query(None, description="Date YYYY-MM-DD. Default: today.", alias="date"),
):
    """Return detailed prediction for one game."""
    target_date = date.today()
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    try:
        svc = get_game_prediction_service()
        detail = svc.get_game_prediction_detail(game_id, target_date)
        if detail is None:
            return {"gameId": game_id, "error": "Game not found or no prediction available"}
        return detail
    except Exception as e:
        logger.error("Failed to fetch game prediction detail", game_id=game_id, error=str(e))
        return {"gameId": game_id, "error": str(e)}


@router.get(
    "/{game_id}",
    summary="Get game details",
    description="Get detailed information about a specific game including teams, scores, status, and timing.",
    response_description="Game information with teams, scores, and status",
    tags=["games_v1"]
)
def game_detail(
    game_id: str = Path(..., description="NBA game ID", example="0022400123")
):
    """Get detailed game information"""
    try:
        # Try to get from today's games first
        live_game_service = LiveGameService()
        game = live_game_service.get_game_by_id(game_id)
        
        if game:
            return {
                "game": {
                    "id": game.game_id,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "quarter": game.quarter,
                    "time_remaining": game.time_remaining,
                    "status": "FINAL" if game.is_final else ("LIVE" if game.quarter else "SCHEDULED"),
                    "is_final": game.is_final
                }
            }
        
        # If not found in today's games, try to fetch from ESPN
        try:
            espn_service = get_espn_service()
            summary = espn_service.get_game_summary(game_id)
            
            if summary:
                # Extract game info from ESPN summary
                competitions = summary.get("header", {}).get("competitions", [])
                if competitions:
                    comp = competitions[0]
                    competitors = comp.get("competitors", [])
                    
                    home_team = None
                    away_team = None
                    home_score = 0
                    away_score = 0
                    
                    for competitor in competitors:
                        team_data = competitor.get("team", {})
                        team_abbr = team_data.get("abbreviation", "")
                        score = competitor.get("score", 0)
                        is_home = competitor.get("homeAway") == "home"
                        
                        if is_home:
                            home_team = team_abbr
                            home_score = score
                        else:
                            away_team = team_abbr
                            away_score = score
                    
                    status_obj = comp.get("status", {})
                    status_type = status_obj.get("type", {})
                    status_id = status_type.get("id", 1)
                    
                    game_status = "SCHEDULED"
                    if status_id == 2:
                        game_status = "LIVE"
                    elif status_id == 3:
                        game_status = "FINAL"
                    
                    return {
                        "game": {
                            "id": game_id,
                            "home_team": home_team,
                            "away_team": away_team,
                            "home_score": home_score,
                            "away_score": away_score,
                            "status": game_status,
                            "is_final": status_id == 3
                        }
                    }
        except Exception:
            pass
        
        # Fallback: return basic info
        return {"game": {"id": game_id, "status": "UNKNOWN"}}
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch game details", game_id=game_id, error=str(e))
        return {"game": {"id": game_id, "status": "ERROR", "error": str(e)}}
