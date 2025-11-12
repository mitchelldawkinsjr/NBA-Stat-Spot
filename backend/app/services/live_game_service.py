"""
Live Game Service - Fetches live NBA game data
Uses API-NBA as primary source, falls back to ESPN, then nba_api
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import structlog
from .api_nba_service import get_api_nba_service
from .over_under_service import LiveGame
from .cache_service import get_cache_service

logger = structlog.get_logger()


class LiveGameService:
    """Service to fetch live NBA games for over/under analysis"""
    
    def __init__(self):
        self.cache = get_cache_service()
        self.api_nba_service = get_api_nba_service()
        # Circuit breaker state for API-NBA
        self._api_nba_failures = 0
        self._api_nba_circuit_open = False
        self._circuit_reset_time = None
    
    def get_todays_games(self) -> List[LiveGame]:
        """
        Fetch all games happening today (live, scheduled, or completed)
        Uses API-NBA as primary source, falls back to ESPN, then nba_api
        Includes caching (60s) and circuit breaker for failing APIs
        
        Returns:
            List of LiveGame objects
        """
        # Check cache first
        cache_key = "todays_games:60s"
        cached = self.cache.get(cache_key)
        if cached is not None:
            # Only return cached if it has games (don't cache empty results)
            if len(cached) > 0:
                logger.debug("Returning cached games", count=len(cached))
                # Convert cached dicts back to LiveGame objects
                return [self._dict_to_live_game(g) for g in cached]
            else:
                logger.debug("Cached result is empty, fetching fresh data")
        
        # Check circuit breaker state for API-NBA
        if self._api_nba_circuit_open:
            # Check if circuit should be reset (5 minute cooldown)
            if self._circuit_reset_time and time.time() >= self._circuit_reset_time:
                logger.info("Resetting API-NBA circuit breaker")
                self._api_nba_circuit_open = False
                self._api_nba_failures = 0
                self._circuit_reset_time = None
            else:
                logger.warning("API-NBA circuit breaker is open, skipping API-NBA")
        
        # Try API-NBA first (unless circuit is open)
        if not self._api_nba_circuit_open:
            try:
                games = self._fetch_from_api_nba()
                if games:
                    # Reset circuit breaker on success
                    self._api_nba_failures = 0
                    self._api_nba_circuit_open = False
                    self._circuit_reset_time = None
                    
                    # Cache successful result (convert LiveGame objects to dicts for JSON serialization)
                    games_dicts = [self._live_game_to_dict(g) for g in games]
                    self.cache.set(cache_key, games_dicts, ttl=60)
                    
                    logger.info("Fetched live games from API-NBA", count=len(games))
                    return games
                else:
                    # API-NBA returned empty (likely no API key or no games)
                    logger.debug("API-NBA returned empty, falling back to ESPN")
            except Exception as e:
                self._api_nba_failures += 1
                logger.warning("API-NBA failed", error=str(e), failures=self._api_nba_failures)
                
                # Open circuit after 3 consecutive failures
                if self._api_nba_failures >= 3:
                    self._api_nba_circuit_open = True
                    self._circuit_reset_time = time.time() + 300  # 5 minute cooldown
                    logger.warning(
                        "API-NBA circuit breaker opened",
                        failures=self._api_nba_failures,
                        reset_time=self._circuit_reset_time
                    )
        
        # Fallback to ESPN
        try:
            logger.info("Attempting to fetch games from ESPN (fallback from API-NBA)")
            games = self._fetch_from_espn()
            if games:
                # Cache successful result (convert LiveGame objects to dicts for JSON serialization)
                games_dicts = [self._live_game_to_dict(g) for g in games]
                self.cache.set(cache_key, games_dicts, ttl=60)
                
                logger.info("Fetched live games from ESPN", count=len(games))
                return games
            else:
                logger.warning("ESPN returned empty list, trying nba_api")
        except Exception as e:
            logger.warning("ESPN failed, trying nba_api", error=str(e), exc_info=True)
        
        # Final fallback to nba_api
        try:
            games = self._fetch_from_nba_api()
            if games:
                # Cache successful result (convert LiveGame objects to dicts for JSON serialization)
                games_dicts = [self._live_game_to_dict(g) for g in games]
                self.cache.set(cache_key, games_dicts, ttl=60)
                
                logger.info("Fetched live games from nba_api", count=len(games))
                return games
            else:
                logger.warning("nba_api returned empty list")
        except Exception as e:
            logger.error("All live game sources failed", error=str(e))
        
        logger.warning("No games fetched from any source")
        return []
    
    def _fetch_from_api_nba(self) -> List[LiveGame]:
        """Fetch live games from API-NBA"""
        api_games = self.api_nba_service.get_live_games()
        logger.info("API-NBA returned games", count=len(api_games))
        live_games = []
        
        for game in api_games:
            try:
                home_team = game.get("home_team", {})
                away_team = game.get("away_team", {})
                
                home_score = home_team.get("score", 0)
                away_score = away_team.get("score", 0)
                period = game.get("period", 0)
                status = game.get("status", "")
                
                # Mark as final if status explicitly says "Final" or if period is 0 (scheduled/not started)
                # For live games, period should be > 0, so they won't be marked as final
                is_final = "Final" in status or period == 0
                
                live_game = LiveGame(
                    game_id=game.get("game_id", ""),
                    home_team=home_team.get("code", ""),
                    away_team=away_team.get("code", ""),
                    home_score=int(home_score) if home_score else 0,
                    away_score=int(away_score) if away_score else 0,
                    quarter=period if period > 0 else 1,
                    time_remaining=game.get("time_remaining", "12:00"),
                    is_final=is_final
                )
                live_games.append(live_game)
                logger.debug(
                    "Parsed API-NBA game",
                    game_id=live_game.game_id,
                    home=live_game.home_team,
                    away=live_game.away_team,
                    period=period,
                    quarter=live_game.quarter,
                    is_final=live_game.is_final,
                    status=status
                )
            except Exception as e:
                logger.warning("Error parsing API-NBA game", error=str(e), game_data=game)
                continue
        
        logger.info("Parsed API-NBA games into LiveGame objects", count=len(live_games))
        return live_games
    
    def _fetch_from_espn(self) -> List[LiveGame]:
        """Fetch live games from ESPN API"""
        from .espn_api_service import get_espn_service
        
        espn_service = get_espn_service()
        scoreboard_data = espn_service.get_scoreboard()
        
        if not scoreboard_data:
            logger.debug("ESPN scoreboard data is None or empty")
            return []
        
        events = scoreboard_data.get("events", [])
        logger.debug("ESPN returned events", count=len(events))
        live_games = []
        
        for event in events:
            try:
                game_id = event.get("id", "")
                if not game_id:
                    logger.debug("Skipping event with no ID")
                    continue
                
                # Convert game_id to string if it's not already
                game_id = str(game_id)
                
                competitions = event.get("competitions", [])
                if not competitions:
                    logger.debug("Skipping event with no competitions", game_id=game_id)
                    continue
                
                comp = competitions[0]
                competitors = comp.get("competitors", [])
                status = comp.get("status", {})
                
                home_team = None
                away_team = None
                home_score = 0
                away_score = 0
                
                for competitor in competitors:
                    team = competitor.get("team", {})
                    score = competitor.get("score", "0")
                    is_home = competitor.get("homeAway") == "home"
                    
                    team_abbr = team.get("abbreviation", "")
                    
                    if is_home:
                        home_team = team_abbr
                        home_score = int(score) if score else 0
                    else:
                        away_team = team_abbr
                        away_score = int(score) if score else 0
                
                status_type = status.get("type", {})
                status_id = int(status_type.get("id", 0)) if status_type.get("id") else 0
                period = status.get("period", 0)
                clock = status.get("displayClock", "")
                
                is_final = status_id == 3 or status_type.get("name") == "STATUS_FINAL"
                
                # Include all games that are not final, or games that have started (period > 0)
                # This includes scheduled games (period=0, not final) and in-progress games
                if not is_final or period > 0:
                    live_game = LiveGame(
                        game_id=game_id,
                        home_team=home_team or "UNK",
                        away_team=away_team or "UNK",
                        home_score=home_score,
                        away_score=away_score,
                        quarter=period if period > 0 else 1,
                        time_remaining=clock if clock else "12:00",
                        is_final=is_final
                    )
                    live_games.append(live_game)
                    logger.debug(
                        "Parsed ESPN game",
                        game_id=game_id,
                        home=home_team,
                        away=away_team,
                        quarter=period,
                        score=f"{away_score}-{home_score}"
                    )
            except Exception as e:
                logger.warning("Error parsing ESPN game", error=str(e), exc_info=True)
                continue
        
        logger.info("Parsed ESPN games into LiveGame objects", count=len(live_games))
        return live_games
    
    def _fetch_from_nba_api(self) -> List[LiveGame]:
        """Fallback: Fetch from nba_api library"""
        from .nba_api_service import NBADataService
        
        games_data = NBADataService.fetch_todays_games()
        live_games = []
        
        for game in games_data:
            try:
                game_id = str(game.get('gameId') or game.get('game_id') or game.get('id', ''))
                if not game_id:
                    continue
                
                home_team_data = game.get('homeTeam') or game.get('home_team') or {}
                away_team_data = game.get('awayTeam') or game.get('away_team') or {}
                
                home_team = self._extract_team_name(home_team_data)
                away_team = self._extract_team_name(away_team_data)
                
                home_score = self._extract_score(home_team_data)
                away_score = self._extract_score(away_team_data)
                
                quarter = game.get('period') or game.get('quarter') or game.get('periodValue', 0)
                time_remaining = game.get('gameClock') or game.get('time_remaining') or game.get('clock', '12:00')
                game_status = game.get('gameStatusText') or game.get('status') or game.get('gameStatus', '')
                
                is_final = (
                    game_status == 'Final' or 
                    game_status == 'Final/OT' or
                    game.get('gameStatus') == 3 or
                    quarter == 0
                )
                
                if not is_final or quarter > 0:
                    live_game = LiveGame(
                        game_id=game_id,
                        home_team=home_team,
                        away_team=away_team,
                        home_score=home_score,
                        away_score=away_score,
                        quarter=quarter if quarter > 0 else 1,
                        time_remaining=time_remaining if time_remaining else '12:00',
                        is_final=is_final
                    )
                    live_games.append(live_game)
            except Exception as e:
                logger.warning("Error parsing nba_api game", error=str(e))
                continue
        
        return live_games
    
    def get_game_by_id(self, game_id: str) -> Optional[LiveGame]:
        """
        Fetch a specific game by ID
        
        Args:
            game_id: Game ID string
            
        Returns:
            LiveGame object or None if not found
        """
        games = self.get_todays_games()
        for game in games:
            if game.game_id == game_id:
                return game
        return None
    
    def _extract_team_name(self, team_data: Dict[str, Any]) -> str:
        """Extract team name from team data structure"""
        if isinstance(team_data, str):
            return team_data
        
        # Try various possible keys
        return (
            team_data.get('teamName') or
            team_data.get('team_name') or
            team_data.get('name') or
            team_data.get('fullName') or
            team_data.get('full_name') or
            team_data.get('teamTricode') or
            team_data.get('tricode') or
            'Unknown'
        )
    
    def _extract_score(self, team_data: Dict[str, Any]) -> int:
        """Extract score from team data structure"""
        if isinstance(team_data, (int, float)):
            return int(team_data)
        
        score = (
            team_data.get('score') or
            team_data.get('points') or
            0
        )
        
        try:
            return int(score)
        except (ValueError, TypeError):
            return 0
    
    def _live_game_to_dict(self, game: LiveGame) -> Dict[str, Any]:
        """Convert LiveGame object to dictionary for caching"""
        return {
            'game_id': game.game_id,
            'home_team': game.home_team,
            'away_team': game.away_team,
            'home_score': game.home_score,
            'away_score': game.away_score,
            'quarter': game.quarter,
            'time_remaining': game.time_remaining,
            'is_final': game.is_final
        }
    
    def _dict_to_live_game(self, game_dict: Dict[str, Any]) -> LiveGame:
        """Convert dictionary back to LiveGame object"""
        return LiveGame(
            game_id=game_dict.get('game_id', ''),
            home_team=game_dict.get('home_team', ''),
            away_team=game_dict.get('away_team', ''),
            home_score=game_dict.get('home_score', 0),
            away_score=game_dict.get('away_score', 0),
            quarter=game_dict.get('quarter', 1),
            time_remaining=game_dict.get('time_remaining', '12:00'),
            is_final=game_dict.get('is_final', False)
        )

