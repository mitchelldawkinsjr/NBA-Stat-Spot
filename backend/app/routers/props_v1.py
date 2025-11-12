from fastapi import APIRouter, Depends, Request, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.nba_api_service import NBADataService
from ..services.prop_engine import PropBetEngine
from ..services.prop_filter import PropFilter
from ..services.daily_props_service import DailyPropsService
from ..services.high_hit_rate_service import HighHitRateService
from ..services.stats_calculator import StatsCalculator
from ..services.settings_service import SettingsService
from ..core.rate_limiter import limiter

router = APIRouter(prefix="/api/v1/props", tags=["props_v1"])

STAT_KEYS = ["pts", "reb", "ast", "tpm"]


def build_suggestions_for_player(player_id: int, season: Optional[str]) -> List[Dict]:
    logs = NBADataService.fetch_player_game_log(player_id, season)
    suggestions: List[Dict] = []
    for sk in STAT_KEYS:
        line = PropBetEngine.determine_line_value(logs, sk)
        suggestions.append(PropBetEngine.evaluate_prop(logs, sk, line))
    return suggestions


class PlayerSuggestRequest(BaseModel):
    """Request model for player prop suggestions"""
    playerId: int = Field(..., description="NBA player ID", example=2544)
    season: Optional[str] = Field(None, description="Season string (e.g., '2025-26'). Defaults to current season.", example="2025-26")
    lastN: Optional[int] = Field(None, description="Number of recent games to consider for analysis", example=10, ge=1)
    home: Optional[str] = Field(None, description="Filter by venue: 'home', 'away', or None for all", example="home")
    marketLines: Optional[Dict[str, float]] = Field(None, description="Market lines to analyze. Keys: PTS, REB, AST, 3PM, PRA", example={"PTS": 24.5, "REB": 8.5})
    direction: Optional[str] = Field(None, description="Direction for all props: 'over' or 'under'. Defaults to 'over'", example="over")
    use_ai: Optional[bool] = Field(True, description="Enable AI features (ML predictions and LLM rationales)", example=True)
    game_date: Optional[str] = Field(None, description="Game date in YYYY-MM-DD format for context", example="2025-01-15")
    opponent_team_id: Optional[int] = Field(None, description="Opponent team ID for matchup analysis", example=1610612744)

    class Config:
        json_schema_extra = {
            "example": {
                "playerId": 2544,
                "season": "2025-26",
                "lastN": 10,
                "marketLines": {"PTS": 24.5, "REB": 8.5},
                "direction": "over",
                "use_ai": True,
                "game_date": "2025-01-15",
                "opponent_team_id": 1610612744
            }
        }


class PropSuggestionResponse(BaseModel):
    """Response model for a single prop suggestion"""
    type: str = Field(..., description="Prop type: PTS, REB, AST, 3PM, or PRA", example="PTS")
    marketLine: float = Field(..., description="The market betting line", example=24.5)
    fairLine: float = Field(..., description="Calculated fair line based on historical data", example=25.2)
    direction: str = Field(..., description="Recommended direction: 'over' or 'under'", example="over")
    confidence: float = Field(..., description="Confidence score (0-100)", example=75.5)
    suggestion: str = Field(..., description="Suggestion: 'strong_over', 'over', 'under', 'strong_under'", example="over")
    hitRate: Optional[float] = Field(None, description="Historical hit rate for this prop", example=0.72)
    hitRateOver: Optional[float] = Field(None, description="Hit rate for over bets", example=0.72)
    hitRateUnder: Optional[float] = Field(None, description="Hit rate for under bets", example=0.28)
    mlConfidence: Optional[float] = Field(None, description="ML model confidence (if AI enabled)", example=78.3)
    mlPredictedLine: Optional[float] = Field(None, description="ML model predicted line (if AI enabled)", example=25.8)
    confidenceSource: Optional[str] = Field(None, description="Source of confidence: 'ml' or 'rule_based'", example="ml")
    rationale: Optional[List[str]] = Field(None, description="Explanation for the suggestion", example=["Based on recent form and hit rate", "Player has exceeded this line in 8 of last 10 games"])
    rationaleSource: Optional[str] = Field(None, description="Source of rationale: 'llm' or 'rule_based'", example="llm")


class PlayerSuggestResponse(BaseModel):
    """Response model for player prop suggestions"""
    suggestions: List[PropSuggestionResponse] = Field(..., description="List of prop suggestions")


@router.post(
    "/player",
    response_model=PlayerSuggestResponse,
    summary="Get AI-powered prop suggestions for a player",
    description="""
    Analyze player prop bets with AI-enhanced predictions.
    
    This endpoint provides comprehensive prop analysis including:
    - Fair line calculations based on historical performance
    - Hit rate analysis for over/under bets
    - AI/ML predictions (if enabled)
    - Detailed rationales explaining the suggestions
    
    **Supported Prop Types:**
    - PTS: Points
    - REB: Rebounds
    - AST: Assists
    - 3PM: Three-pointers made
    - PRA: Points + Rebounds + Assists
    
    **AI Features:**
    When `use_ai` is enabled, the endpoint uses machine learning models to:
    - Predict player performance based on matchup, venue, and recent form
    - Generate natural language rationales using LLM
    - Provide ML-based confidence scores
    
    **Rate Limit:** 30 requests per minute per IP
    """,
    response_description="List of prop suggestions with confidence scores and rationales",
    tags=["props_v1"]
)
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute per IP
def suggest_player_props(request: Request, req: PlayerSuggestRequest, db: Session = Depends(get_db)):
    # Default season fallback
    season = req.season or "2025-26"
    try:
        logs = NBADataService.fetch_player_game_log(req.playerId, season)
    except Exception:
        # Gracefully degrade instead of 500
        return {"suggestions": []}
    # Optional venue filter
    if req.home in ("home", "away"):
        is_home = req.home == "home"
        filtered: List[Dict] = []
        for g in logs:
            matchup = (g.get("matchup") or "").lower()
            at_away = "@" in matchup
            vs_home = "vs" in matchup
            if is_home and vs_home:
                filtered.append(g)
            elif (not is_home) and at_away:
                filtered.append(g)
        logs = filtered
    # Optional lastN slice
    if req.lastN and req.lastN > 0:
        logs = logs[-req.lastN:]
    
    # Filter by minimum average minutes (default 22 minutes)
    # Calculate average minutes from recent games
    if logs:
        minutes_list = [float(g.get("minutes", 0) or 0) for g in logs if g.get("minutes")]
        if minutes_list:
            avg_minutes = sum(minutes_list) / len(minutes_list)
            if avg_minutes < 22.0:
                # Player doesn't meet minimum minutes threshold
                return {"suggestions": []}
    
    # Enrich PRA
    for g in logs:
        g["pra"] = float(g.get("pts", 0) or 0) + float(g.get("reb", 0) or 0) + float(g.get("ast", 0) or 0)

    suggestions: List[Dict] = []
    lines = req.marketLines or {}
    # Use provided direction or default to "over"
    direction = (req.direction or "over").lower()
    if direction not in ("over", "under"):
        direction = "over"
    
    # Get player name for LLM rationale
    player_name = None
    try:
        all_players = NBADataService.fetch_all_players_including_rookies()
        player = next((p for p in all_players if p.get("id") == req.playerId), None)
        if player:
            player_name = player.get("full_name")
    except Exception:
        pass
    
    # Parse game_date if provided
    game_date_obj = None
    if req.game_date:
        try:
            from datetime import datetime
            game_date_obj = datetime.strptime(req.game_date, "%Y-%m-%d").date()
        except Exception:
            pass
    
    # Determine if home game (simplified - would need game context)
    is_home_game = True  # Default assumption
    
    # Map display -> stat key
    key_map = {"PTS": "pts", "REB": "reb", "AST": "ast", "3PM": "tpm", "PRA": "pra"}
    for disp_key, market_line in lines.items():
        stat_key = key_map.get(disp_key)
        if stat_key is None:
            continue
        try:
            fair = PropBetEngine.determine_line_value(logs, stat_key)
            
            # Check global AI setting (overrides request parameter)
            ai_enabled_globally = SettingsService.get_ai_enabled(db)
            use_ai = req.use_ai and ai_enabled_globally
            
            # Use AI-enhanced evaluation if enabled and context available
            if use_ai and game_date_obj:
                ev = PropBetEngine.evaluate_prop_with_ml(
                    logs, stat_key, float(market_line), direction,
                    player_id=req.playerId,
                    game_date=game_date_obj,
                    opponent_team_id=req.opponent_team_id,
                    is_home_game=is_home_game,
                    season=season
                )
            else:
                # Fallback to rule-based evaluation
                ev = PropBetEngine.evaluate_prop(logs, stat_key, float(market_line), direction)
            
            # Always calculate both hit rates for completeness
            hit_rate_over = StatsCalculator.calculate_hit_rate(logs, float(market_line), stat_key, "over")
            hit_rate_under = StatsCalculator.calculate_hit_rate(logs, float(market_line), stat_key, "under")
            
            # Build suggestion response
            suggestion = {
                "type": disp_key,
                "marketLine": float(market_line),
                "fairLine": float(fair),
                "direction": direction,
                "confidence": ev.get("confidence"),
                "suggestion": ev.get("suggestion"),
                "hitRate": ev.get("stats", {}).get("hit_rate"),
                "hitRateOver": hit_rate_over,
                "hitRateUnder": hit_rate_under,
            }
            
            # Add AI-enhanced fields if available
            if use_ai:
                if ev.get("ml_available"):
                    suggestion["mlConfidence"] = ev.get("ml_confidence")
                    suggestion["mlPredictedLine"] = ev.get("ml_predicted_line")
                    suggestion["confidenceSource"] = ev.get("confidence_source", "rule_based")
                
                # Add LLM rationale if available
                rationale = ev.get("rationale", {})
                if rationale.get("llm"):
                    suggestion["rationale"] = [
                        rationale.get("summary", "Based on recent form and hit rate"),
                        rationale.get("llm")
                    ]
                    suggestion["rationaleSource"] = rationale.get("source", "rule_based")
                else:
                    suggestion["rationale"] = [rationale.get("summary", "Based on recent form and hit rate")]
                    suggestion["rationaleSource"] = "rule_based"
            else:
                suggestion["rationale"] = [ev.get("rationale", {}).get("summary", "Based on recent form and hit rate")]
            
            suggestions.append(suggestion)
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Error evaluating prop", prop_type=disp_key, error=str(e))
            continue
    
    # Convert dict suggestions to PropSuggestionResponse objects
    response_suggestions = [
        PropSuggestionResponse(**s) for s in suggestions
    ]
    return PlayerSuggestResponse(suggestions=response_suggestions)

@router.get(
    "/daily",
    summary="Get top daily prop suggestions",
    description="""
    Get the best prop suggestions for all players playing on a specific date.
    
    This endpoint scans all players with games scheduled for the target date and returns
    the top prop suggestions ranked by confidence. Results are cached for performance.
    
    **Features:**
    - Automatically filters to players with games on the target date
    - Returns props for multiple stat types (PTS, REB, AST, 3PM, PRA)
    - Includes player information, game context, and confidence scores
    - Results are cached for 24 hours to improve response times
    
    **Filtering:**
    - Use `min_confidence` to filter by minimum confidence score (0-100)
    - Use `limit` to restrict the number of results
    - Use `last_n` to control how many recent games to consider
    
    **Caching:**
    Results are cached per date. The first request for a date may take longer,
    but subsequent requests will be served from cache.
    """,
    response_description="List of daily prop suggestions with player and game information",
    tags=["props_v1"]
)
def daily_props(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score (0-100) to filter results", example=70.0, ge=0, le=100),
    limit: Optional[int] = Query(None, description="Maximum number of results to return. No limit by default.", example=50, ge=1),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26"),
    last_n: Optional[int] = Query(None, description="Number of recent games to consider for analysis", example=10, ge=1)
):
    """
    Get top daily props for all players playing today.
    Uses cached data if available (cached for today), otherwise fetches fresh data.
    """
    from datetime import date as date_type, datetime
    from ..routers.admin_v1 import _get_daily_props_cache, _set_daily_props_cache
    
    # Determine the target date - use provided date or today
    if date:
        target_date_str = date
    else:
        target_date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Check if we have valid cached data for the requested date
    cached_data = _get_daily_props_cache(target_date_str)
    
    if cached_data:
        # Return cached data, but filter by gameDate to ensure we only return props for the requested date
        items = cached_data.get("items", [])
        # Filter by gameDate to ensure we only return props for today
        # If gameDate is not set, include the item (assume it's for today since cache is for today)
        filtered_items = []
        for item in items:
            item_date = item.get("gameDate") or item.get("game_date")
            if item_date:
                # If gameDate exists, it must match the target date
                if item_date == target_date_str or item_date.startswith(target_date_str):
                    filtered_items.append(item)
            else:
                # If no gameDate, include it (cache is for today, so items should be for today)
                filtered_items.append(item)
        items = filtered_items
        # Apply filters if provided
        if min_confidence:
            items = [item for item in items if (item.get("confidence") or 0) >= min_confidence]
        
        # Apply limit if provided (but return all by default)
        if limit and limit > 0:
            items = items[:limit]
        
        # Return all items - frontend will handle pagination
        return {
            "items": items,
            "total": len(items),
            "cached": True,
            "cachedAt": None  # Cache service handles TTL internally
        }
    
    # No valid cache for requested date, fetch fresh data and cache it
    # Use try/except for timeout protection
    try:
        # Fetch comprehensive results - scan whole league
        # If limit is provided, use it; otherwise fetch comprehensive results for caching
        fetch_limit = limit if limit and limit > 0 else 500  # Fetch comprehensive results
        result = DailyPropsService.get_top_props_for_date(
            date=date,
            season=season,
            min_confidence=min_confidence,
            limit=fetch_limit,
            last_n=last_n  # Use provided last_n or default (10 games)
        )
        
        all_items = result.get("items", [])
        
        # Auto-populate cache if this is for today and cache is empty/invalid
        if not date or target_date_str == datetime.now().strftime("%Y-%m-%d"):
            # Check if cache exists for today
            today_cached = _get_daily_props_cache(target_date_str)
            if not today_cached:
                # Update cache synchronously to ensure it's populated for next request
                # This ensures comprehensive results are cached
                try:
                    _set_daily_props_cache({"items": all_items}, target_date=target_date_str, ttl=86400)
                except Exception:
                    pass  # Cache update failed, but don't fail the request
        
        # Return all items - frontend will handle pagination
        return {
            "items": all_items,
            "total": len(all_items),
            "cached": False
        }
    except Exception as e:
        # If there's an error, return empty result with error message
        import structlog
        logger = structlog.get_logger()
        logger.error("Error fetching daily props", error=str(e))
        return {
            "items": [],
            "total": 0,
            "returned": 0,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "season": season or "2025-26",
            "error": "Request failed. Please try again.",
            "cached": False
        }

@router.get(
    "/player/{player_id}",
    summary="Get basic prop suggestions for a player",
    description="""
    Get basic prop suggestions for a specific player without market lines.
    
    This is a simplified endpoint that returns suggestions for standard prop types
    (PTS, REB, AST, 3PM) based on the player's historical performance.
    
    For more detailed analysis with specific market lines, use POST `/api/v1/props/player`.
    """,
    response_description="List of basic prop suggestions",
    tags=["props_v1"]
)
def player_props(
    player_id: int = Path(..., description="NBA player ID", example=2544),
    date: Optional[str] = Query(None, description="Game date in YYYY-MM-DD format", example="2025-01-15"),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    sugs = build_suggestions_for_player(player_id, season)
    return {"items": sugs}

@router.get("/game/{game_id}")
def game_props(
    game_id: str = Path(..., description="NBA game ID", example="0022400123"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score (0-100) to filter results", example=65.0, ge=0, le=100),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    """
    Get prop suggestions for all players in a specific game.
    
    Fetches game details to identify teams, then generates prop suggestions
    for players on both teams.
    """
    try:
        from ..services.live_game_service import LiveGameService
        from ..services.espn_api_service import get_espn_service
        from ..services.team_player_service import TeamPlayerService
        from ..services.nba_api_service import NBADataService
        
        # Get game details to identify teams
        live_game_service = LiveGameService()
        game = live_game_service.get_game_by_id(game_id)
        
        home_team_abbr = None
        away_team_abbr = None
        
        if game:
            home_team_abbr = game.home_team
            away_team_abbr = game.away_team
        else:
            # Try ESPN
            try:
                espn_service = get_espn_service()
                summary = espn_service.get_game_summary(game_id)
                if summary:
                    competitions = summary.get("header", {}).get("competitions", [])
                    if competitions:
                        comp = competitions[0]
                        competitors = comp.get("competitors", [])
                        for competitor in competitors:
                            team_data = competitor.get("team", {})
                            team_abbr = team_data.get("abbreviation", "")
                            is_home = competitor.get("homeAway") == "home"
                            if is_home:
                                home_team_abbr = team_abbr
                            else:
                                away_team_abbr = team_abbr
            except Exception:
                pass
        
        if not home_team_abbr or not away_team_abbr:
            return {"items": [], "error": "Could not identify teams for this game"}
        
        # Get team IDs from abbreviations
        teams = NBADataService.fetch_all_teams()
        home_team = next((t for t in teams if t.get("abbreviation") == home_team_abbr), None)
        away_team = next((t for t in teams if t.get("abbreviation") == away_team_abbr), None)
        
        if not home_team or not away_team:
            return {"items": [], "error": "Could not find team IDs"}
        
        home_team_id = home_team.get("id")
        away_team_id = away_team.get("id")
        
        # Get players from both teams
        home_players = TeamPlayerService.get_players_for_team(home_team_id)
        away_players = TeamPlayerService.get_players_for_team(away_team_id)
        
        all_players = home_players + away_players
        
        if not all_players:
            return {"items": [], "error": "No players found for teams in this game"}
        
        # Generate props for each player
        all_suggestions = []
        for player in all_players:
            player_id = player.get("id")
            if not player_id:
                continue
            
            try:
                suggestions = build_suggestions_for_player(player_id, season)
                for sug in suggestions:
                    # Filter by confidence if specified
                    if min_confidence is None or (sug.get("confidence") or 0) >= min_confidence:
                        all_suggestions.append(sug)
            except Exception:
                continue
        
        # Sort by confidence (highest first)
        all_suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return {"items": all_suggestions, "game_id": game_id, "home_team": home_team_abbr, "away_team": away_team_abbr}
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch game props", game_id=game_id, error=str(e))
        return {"items": [], "error": str(e)}

@router.get("/trending")
def trending_props(
    limit: int = Query(10, description="Maximum number of trending props to return", example=10, ge=1, le=50),
    min_confidence: Optional[float] = Query(70.0, description="Minimum confidence score (0-100)", example=70.0, ge=0, le=100),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26")
):
    """
    Get trending prop suggestions based on recent performance and high confidence.
    
    Trending props are determined by:
    - High confidence scores
    - Recent strong performance (exceeding lines consistently)
    - High hit rates
    """
    try:
        # Get daily props as base
        daily_items = daily_props(
            min_confidence=min_confidence,
            season=season,
            limit=limit * 3  # Get more to filter
        ).get("items", [])
        
        if not daily_items:
            return {"items": []}
        
        # Score and rank by trending factors
        trending_items = []
        for item in daily_items:
            confidence = item.get("confidence", 0)
            hit_rate = item.get("hitRate", 0)
            
            # Calculate trending score
            # Higher confidence + higher hit rate = more trending
            trending_score = (confidence * 0.6) + (hit_rate * 100 * 0.4)
            
            # Only include items with good trending score
            if trending_score >= (min_confidence or 70):
                item["trending_score"] = trending_score
                trending_items.append(item)
        
        # Sort by trending score (highest first)
        trending_items.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
        
        # Return top N
        return {"items": trending_items[:limit]}
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch trending props", error=str(e))
        return {"items": []}

@router.get(
    "/high-hit-rate",
    summary="Get props with high historical hit rates",
    description="""
    Get prop suggestions that have high historical hit rates (75%+ by default).
    
    This endpoint focuses on props where the player has consistently hit the over
    or under in recent games. These are typically safer bets with higher probability
    of success.
    
    **Hit Rate Calculation:**
    The hit rate is calculated based on the player's performance in recent games
    (controlled by `last_n` parameter). A hit rate of 0.75 means the player has
    exceeded (for over) or stayed under (for under) the line in 75% of recent games.
    
    **Use Cases:**
    - Find "safe" bets with high probability
    - Identify players with consistent performance patterns
    - Build conservative parlay bets
    
    **Caching:**
    Results are cached per date for 24 hours to improve performance.
    """,
    response_description="List of high hit rate prop suggestions",
    tags=["props_v1"]
)
def high_hit_rate_props(
    date: Optional[str] = Query(None, description="Target date in YYYY-MM-DD format. Defaults to today.", example="2025-01-15"),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26')", example="2025-26"),
    min_hit_rate: float = Query(0.75, description="Minimum hit rate threshold (0.0-1.0). Default 0.75 (75%)", example=0.75, ge=0.0, le=1.0),
    limit: int = Query(10, description="Maximum number of results to return", example=10, ge=1),
    last_n: Optional[int] = Query(None, description="Number of recent games to consider for hit rate calculation", example=10, ge=1)
):
    """
    Get props with high historical hit rates for players playing today.
    Uses cached data if available (cached for today), otherwise fetches fresh data.
    
    Args:
        date: Date to check (YYYY-MM-DD), defaults to today
        season: Season string, defaults to current season
        min_hit_rate: Minimum hit rate threshold (0.0-1.0), default 0.75 (75%)
        limit: Maximum number of results to return
        last_n: Number of recent games to consider for hit rate calculation
    """
    from datetime import datetime
    from ..routers.admin_v1 import _get_high_hit_rate_cache, _set_high_hit_rate_cache
    
    # Determine the target date - use provided date or today
    if date:
        target_date_str = date
    else:
        target_date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Check if we have valid cached data for the requested date
    cached_data = _get_high_hit_rate_cache(target_date_str)
    
    if cached_data:
        # Return cached data, but filter by gameDate to ensure we only return props for the requested date
        items = cached_data.get("items", [])
        # Filter by gameDate to ensure we only return props for today
        # If gameDate is not set, include the item (assume it's for today since cache is for today)
        filtered_items = []
        for item in items:
            item_date = item.get("gameDate") or item.get("game_date")
            if item_date:
                # If gameDate exists, it must match the target date
                if item_date == target_date_str or item_date.startswith(target_date_str):
                    filtered_items.append(item)
            else:
                # If no gameDate, include it (cache is for today, so items should be for today)
                filtered_items.append(item)
        items = filtered_items
        # Apply filters if provided (cache uses default 0.75, but we can filter further)
        if min_hit_rate > 0.75:
            items = [item for item in items if (item.get("hitRate", 0) / 100) >= min_hit_rate]
        if limit:
            items = items[:limit]
        result = cached_data.copy()
        result["items"] = items
        result["cached"] = True
        result["cachedAt"] = None  # Cache service handles TTL internally
        return result
    
    # No valid cache for requested date, fetch fresh data
    result = HighHitRateService.get_high_hit_rate_bets(
        date=date,
        season=season,
        min_hit_rate=min_hit_rate,
        limit=limit,
        last_n=last_n
    )
    result["cached"] = False
    return result

@router.get(
    "/types",
    summary="Get available prop types",
    description="Returns a list of all supported prop bet types in the system.",
    response_description="List of available prop types",
    tags=["props_v1"]
)
def prop_types():
    """Get list of available prop bet types"""
    return {"items": ["points", "rebounds", "assists", "3pm", "steals", "blocks"]}
