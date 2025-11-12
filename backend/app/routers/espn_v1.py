"""
ESPN API Router
Provides endpoints for ESPN NBA data features
"""
from fastapi import APIRouter, Query, Request
from typing import Optional
import structlog
from ..services.espn_api_service import get_espn_service
from ..core.rate_limiter import limiter
from ..core.error_handler import APIError

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/espn", tags=["espn_v1"])


@router.get("/scoreboard")
@limiter.limit("30/minute")
def get_scoreboard(request: Request, date: Optional[str] = Query(None, description="Date in YYYYMMDD format")):
    """
    Get live scoreboard with all games for a date.
    
    Args:
        date: Optional date in YYYYMMDD format (default: today)
        
    Returns:
        Scoreboard data with all games
    """
    try:
        espn_service = get_espn_service()
        scoreboard_data = espn_service.get_scoreboard(date=date)
        
        if scoreboard_data is None:
            raise APIError("Failed to fetch scoreboard", status_code=500)
        
        return scoreboard_data
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching ESPN scoreboard", error=str(e))
        raise APIError(f"Failed to fetch scoreboard: {str(e)}", status_code=500)


@router.get("/games/{game_id}/summary")
@limiter.limit("30/minute")
def get_game_summary(request: Request, game_id: str):
    """
    Get game summary/box score for a specific game.
    
    Args:
        game_id: Game/event ID
        
    Returns:
        Game summary/box score data
    """
    try:
        espn_service = get_espn_service()
        summary = espn_service.get_game_summary(game_id)
        
        if summary is None:
            raise APIError(f"Game {game_id} not found", status_code=404)
        
        return summary
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching game summary", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch game summary: {str(e)}", status_code=500)


@router.get("/games/{game_id}/playbyplay")
@limiter.limit("30/minute")
def get_play_by_play(request: Request, game_id: str):
    """
    Get play-by-play data for a specific game.
    
    Args:
        game_id: Game/event ID
        
    Returns:
        Play-by-play data
    """
    try:
        espn_service = get_espn_service()
        playbyplay = espn_service.get_play_by_play(game_id)
        
        if playbyplay is None:
            raise APIError(f"Play-by-play data for game {game_id} not found", status_code=404)
        
        return playbyplay
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching play-by-play", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch play-by-play: {str(e)}", status_code=500)


@router.get("/games/{game_id}/gamecast")
@limiter.limit("30/minute")
def get_gamecast(request: Request, game_id: str):
    """
    Get gamecast data (advanced game data) for a specific game.
    
    Args:
        game_id: Game/event ID
        
    Returns:
        Gamecast data
    """
    try:
        espn_service = get_espn_service()
        gamecast = espn_service.get_gamecast(game_id)
        
        if gamecast is None:
            raise APIError(f"Gamecast data for game {game_id} not found", status_code=404)
        
        return gamecast
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching gamecast", game_id=game_id, error=str(e))
        raise APIError(f"Failed to fetch gamecast: {str(e)}", status_code=500)


@router.get("/teams")
@limiter.limit("30/minute")
def get_teams(request: Request):
    """
    Get all NBA teams.
    
    Returns:
        List of all NBA teams
    """
    try:
        espn_service = get_espn_service()
        teams = espn_service.get_teams()
        return {"teams": teams}
    except Exception as e:
        logger.error("Error fetching teams", error=str(e))
        raise APIError(f"Failed to fetch teams: {str(e)}", status_code=500)


@router.get("/teams/{team_id}")
@limiter.limit("30/minute")
def get_team_info(request: Request, team_id: str):
    """
    Get information about a specific team.
    
    Args:
        team_id: Team slug (e.g., "lal", "bos")
        
    Returns:
        Team information
    """
    try:
        espn_service = get_espn_service()
        team_info = espn_service.get_team_info(team_id)
        
        if team_info is None:
            raise APIError(f"Team {team_id} not found", status_code=404)
        
        return team_info
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching team info", team_id=team_id, error=str(e))
        raise APIError(f"Failed to fetch team info: {str(e)}", status_code=500)


@router.get("/teams/{team_id}/roster")
@limiter.limit("30/minute")
def get_team_roster(request: Request, team_id: str):
    """
    Get team roster.
    
    Args:
        team_id: Team slug (e.g., "lal", "bos")
        
    Returns:
        Team roster
    """
    try:
        espn_service = get_espn_service()
        roster = espn_service.get_team_roster(team_id)
        return {"roster": roster}
    except Exception as e:
        logger.error("Error fetching team roster", team_id=team_id, error=str(e))
        raise APIError(f"Failed to fetch team roster: {str(e)}", status_code=500)


@router.get("/teams/{team_id}/schedule")
@limiter.limit("30/minute")
def get_team_schedule(request: Request, team_id: str):
    """
    Get team schedule (upcoming and past games).
    
    Args:
        team_id: Team slug (e.g., "lal", "bos")
        
    Returns:
        Team schedule
    """
    try:
        espn_service = get_espn_service()
        schedule = espn_service.get_team_schedule(team_id)
        return {"schedule": schedule}
    except Exception as e:
        logger.error("Error fetching team schedule", team_id=team_id, error=str(e))
        raise APIError(f"Failed to fetch team schedule: {str(e)}", status_code=500)


@router.get("/players/{player_id}")
@limiter.limit("30/minute")
def get_player_info(request: Request, player_id: str):
    """
    Get player information.
    
    Args:
        player_id: Player ID
        
    Returns:
        Player information
    """
    try:
        espn_service = get_espn_service()
        player_info = espn_service.get_player_info(player_id)
        
        if player_info is None:
            raise APIError(f"Player {player_id} not found", status_code=404)
        
        return player_info
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching player info", player_id=player_id, error=str(e))
        raise APIError(f"Failed to fetch player info: {str(e)}", status_code=500)


@router.get("/standings")
@limiter.limit("30/minute")
def get_standings(request: Request):
    """
    Get league and conference standings.
    
    Returns:
        Standings data
    """
    try:
        espn_service = get_espn_service()
        standings = espn_service.get_standings()
        
        if standings is None:
            raise APIError("Failed to fetch standings", status_code=500)
        
        return standings
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching standings", error=str(e))
        raise APIError(f"Failed to fetch standings: {str(e)}", status_code=500)


@router.get("/news")
@limiter.limit("30/minute")
def get_news(request: Request):
    """
    Get NBA news feed aggregated from multiple sources (ESPN and Yahoo Sports).
    
    Returns:
        List of news articles from all sources
    """
    try:
        from ..services.news_context_service import get_news_context_service
        
        news_service = get_news_context_service()
        articles = []
        
        # Fetch from ESPN
        espn_service = get_espn_service()
        espn_news = espn_service.get_news()
        if espn_news:
            articles.extend(espn_news)
        
        # Fetch from Yahoo Sports RSS
        yahoo_articles = news_service._fetch_yahoo_rss_news()
        articles.extend(yahoo_articles)
        
        # Sort by published date (newest first)
        # Handle both ESPN (publishDate) and Yahoo (published) formats
        def get_publish_date(article):
            # Try both field names and normalize to ISO format string
            date_str = article.get("published") or article.get("publishDate") or ""
            return date_str
        
        articles.sort(key=get_publish_date, reverse=True)
        
        return {"articles": articles}
    except Exception as e:
        logger.error("Error fetching news", error=str(e))
        raise APIError(f"Failed to fetch news: {str(e)}", status_code=500)


@router.post("/news/refresh")
@limiter.limit("10/minute")
def refresh_news_cache(request: Request):
    """
    Refresh the news cache by clearing cached news data.
    This will force fresh news to be fetched on the next request.
    
    Returns:
        Success message with number of cache entries cleared
    """
    try:
        from ..services.cache_service import get_cache_service
        
        cache = get_cache_service()
        count = 0
        
        # Clear ESPN news cache
        espn_deleted = cache.delete("espn:news:15m")
        if espn_deleted:
            count += 1
        
        # Clear Yahoo RSS news cache
        yahoo_deleted = cache.delete("yahoo_rss_news:15m")
        if yahoo_deleted:
            count += 1
        
        # Also clear any player/team news context caches (optional - more aggressive)
        # Uncomment if you want to clear all news-related caches:
        # player_news_count = cache.clear_pattern("player_news:*")
        # team_news_count = cache.clear_pattern("team_news:*")
        # count += player_news_count + team_news_count
        
        logger.info("News cache refreshed", entries_cleared=count)
        
        return {
            "message": "News cache refreshed successfully",
            "entries_cleared": count,
            "caches_cleared": ["espn:news:15m", "yahoo_rss_news:15m"]
        }
    except Exception as e:
        logger.error("Error refreshing news cache", error=str(e))
        raise APIError(f"Failed to refresh news cache: {str(e)}", status_code=500)


@router.get("/injuries")
@limiter.limit("30/minute")
def get_injuries(request: Request):
    """
    Get injury reports per team.
    
    Returns:
        Injuries data
    """
    try:
        espn_service = get_espn_service()
        injuries = espn_service.get_injuries()
        
        if injuries is None:
            raise APIError("Failed to fetch injuries", status_code=500)
        
        return injuries
    except APIError:
        raise
    except Exception as e:
        logger.error("Error fetching injuries", error=str(e))
        raise APIError(f"Failed to fetch injuries: {str(e)}", status_code=500)


@router.get("/transactions")
@limiter.limit("30/minute")
def get_transactions(request: Request):
    """
    Get recent trades and signings.
    
    Returns:
        List of transactions
    """
    try:
        espn_service = get_espn_service()
        transactions = espn_service.get_transactions()
        return {"transactions": transactions}
    except Exception as e:
        logger.error("Error fetching transactions", error=str(e))
        raise APIError(f"Failed to fetch transactions: {str(e)}", status_code=500)

