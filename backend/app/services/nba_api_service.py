from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import time
from ..services.cache_service import get_cache_service

try:
    from nba_api.stats.static import teams as static_teams
    from nba_api.stats.static import players as static_players
    from nba_api.stats.endpoints import playergamelog, commonallplayers
    from nba_api.live.nba.endpoints import scoreboard
    from nba_api.stats.endpoints import scoreboardv2
    
    # Configure requests library timeout for nba_api
    # Only patch if requests is available and not already patched
    try:
        import requests
        if not hasattr(requests, '_nba_api_patched'):
            # Increase default timeout from 30s to 60s for NBA API calls
            # This patches both direct requests and Session objects used by nba_api
            try:
                original_get = requests.get
                original_post = requests.post
                
                def patched_get(*args, **kwargs):
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = 60.0  # 60 second timeout
                    return original_get(*args, **kwargs)
                
                def patched_post(*args, **kwargs):
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = 60.0  # 60 second timeout
                    return original_post(*args, **kwargs)
                
                # Patch requests methods used by nba_api
                requests.get = patched_get
                requests.post = patched_post
                
                # Also patch Session.request if available
                if hasattr(requests, 'Session') and hasattr(requests.Session, 'request'):
                    original_session_request = requests.Session.request
                    
                    def patched_session_request(self, method, url, **kwargs):
                        if 'timeout' not in kwargs:
                            kwargs['timeout'] = 60.0  # 60 second timeout
                        return original_session_request(self, method, url, **kwargs)
                    
                    requests.Session.request = patched_session_request
                
                requests._nba_api_patched = True  # Mark as patched to avoid double-patching
            except (AttributeError, TypeError):
                # If patching fails due to missing attributes, silently continue
                pass
    except Exception:
        # If patching fails, silently continue - nba_api might still work with default timeout
        # Don't log here as structlog might not be initialized yet during module import
        pass
except Exception:  # pragma: no cover
    static_teams = None
    static_players = None
    playergamelog = None
    commonallplayers = None
    scoreboard = None
    scoreboardv2 = None


class NBADataService:
    @staticmethod
    def fetch_all_teams() -> List[Dict[str, Any]]:
        """
        Fetch all NBA teams. Cached for 24 hours with date-based key for daily invalidation.
        Uses CacheService (Redis/SQLite) for persistence across container restarts.
        """
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:teams:{today_str}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch if not cached
        if static_teams is None:
            return []
        result = static_teams.get_teams()
        
        # Cache for 24 hours (86400 seconds)
        cache.set(cache_key, result, ttl=86400)
        return result

    @staticmethod
    def fetch_active_players() -> List[Dict[str, Any]]:
        """
        Fetch active players. Cached for 24 hours with date-based key for daily invalidation.
        Uses CacheService (Redis/SQLite) for persistence across container restarts.
        """
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:players_active:{today_str}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch if not cached
        if static_players is None:
            return []
        result = [p for p in static_players.get_players() if p.get("is_active")]
        
        # Cache for 24 hours
        cache.set(cache_key, result, ttl=86400)
        return result
    
    @staticmethod
    def fetch_all_players_including_rookies() -> List[Dict[str, Any]]:
        """Fetch all players including rookies who may not be marked as active yet.
        Uses CommonAllPlayers endpoint to get current season players with team_id,
        then falls back to static players for historical players.
        Cached for 24 hours with date-based key for daily invalidation.
        Uses CacheService (Redis/SQLite) for persistence across container restarts."""
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:players_all_including_rookies:{today_str}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch if not cached
        all_players: List[Dict[str, Any]] = []
        
        # First, get current season players with team_id from CommonAllPlayers
        if commonallplayers is not None:
            try:
                cap = commonallplayers.CommonAllPlayers(is_only_current_season=1)
                data = cap.get_dict()
                result_sets = data.get("resultSets", [])
                if result_sets:
                    headers = result_sets[0].get("headers", [])
                    rows = result_sets[0].get("rowSet", [])
                    
                    # Find column indices
                    try:
                        person_id_idx = headers.index("PERSON_ID")
                        display_first_last_idx = headers.index("DISPLAY_FIRST_LAST")
                        team_id_idx = headers.index("TEAM_ID")
                        roster_status_idx = headers.index("ROSTERSTATUS") if "ROSTERSTATUS" in headers else None
                        # Try to find position and jersey_number if available
                        position_idx = headers.index("POSITION") if "POSITION" in headers else None
                        jersey_idx = headers.index("JERSEY") if "JERSEY" in headers else None
                    except ValueError:
                        # Fallback indices
                        person_id_idx = 0
                        display_first_last_idx = 2
                        team_id_idx = 8
                        roster_status_idx = 3
                        position_idx = None
                        jersey_idx = None
                    
                    for row in rows:
                        if len(row) > max(person_id_idx, display_first_last_idx, team_id_idx):
                            player_id = row[person_id_idx] if person_id_idx < len(row) else None
                            full_name = row[display_first_last_idx] if display_first_last_idx < len(row) else "Unknown"
                            team_id = row[team_id_idx] if team_id_idx < len(row) else None
                            is_active = row[roster_status_idx] == 1 if roster_status_idx and roster_status_idx < len(row) else True
                            position = row[position_idx] if position_idx is not None and position_idx < len(row) else None
                            jersey_number = row[jersey_idx] if jersey_idx is not None and jersey_idx < len(row) else None
                            
                            if player_id:
                                all_players.append({
                                    "id": player_id,
                                    "full_name": full_name,
                                    "first_name": full_name.split()[0] if full_name and " " in full_name else "",
                                    "last_name": " ".join(full_name.split()[1:]) if full_name and " " in full_name else full_name,
                                    "team_id": team_id,
                                    "is_active": is_active,
                                    "position": position,
                                    "jersey_number": jersey_number
                                })
            except Exception:
                pass
        
        # Fallback to static players if CommonAllPlayers failed or for historical players
        # Also merge position and jersey_number from static players for existing players
        if static_players is not None:
            static_players_list = static_players.get_players()
            # Create a map of static players by ID for easy lookup
            static_players_by_id = {p.get("id"): p for p in static_players_list}
            
            # Update existing players with position/jersey_number from static if missing
            for player in all_players:
                player_id = player.get("id")
                if player_id in static_players_by_id:
                    static_player = static_players_by_id[player_id]
                    # Only update if not already set from CommonAllPlayers
                    if not player.get("position") and static_player.get("position"):
                        player["position"] = static_player.get("position")
                    if not player.get("jersey_number") and static_player.get("jersey_number"):
                        player["jersey_number"] = static_player.get("jersey_number")
            
            # Add static players that aren't already in our list (by ID)
            existing_ids = {p.get("id") for p in all_players}
            for p in static_players_list:
                if p.get("id") not in existing_ids:
                    all_players.append(p)
        
        # Cache for 24 hours
        cache.set(cache_key, all_players, ttl=86400)
        return all_players

    @staticmethod
    def _fetch_player_game_log_impl(player_id: int, season: Optional[str]) -> List[Dict[str, Any]]:
        """Internal implementation of fetch_player_game_log without caching.
        Includes retry logic with exponential backoff for handling timeouts."""
        if playergamelog is None:
            return []
        
        import structlog
        logger = structlog.get_logger()
        
        # Default to current season if not provided
        season_to_use = season or "2025-26"
        
        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2.0  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                gl = playergamelog.PlayerGameLog(player_id=player_id, season=season_to_use)
                df = gl.get_data_frames()[0]
                
                # Log available columns for debugging
                if len(df) > 0:
                    logger.info(
                        "Player game log API response",
                        player_id=player_id,
                        season=season_to_use,
                        row_count=len(df),
                        available_columns=list(df.columns),
                        sample_row=df.iloc[0].to_dict() if len(df) > 0 else None
                    )
                
                items: List[Dict[str, Any]] = []
                for idx, row in df.iterrows():
                    # Parse minutes from "MM:SS" format to float
                    # Try multiple possible column names
                    min_str = None
                    min_col_found = None
                    for col_name in ["MIN", "MINUTES", "MP"]:
                        if col_name in row.index:
                            min_val = row.get(col_name)
                            if min_val is not None and str(min_val).strip():
                                min_str = str(min_val).strip()
                                min_col_found = col_name
                                break
                    
                    minutes = 0.0
                    if min_str:
                        try:
                            # Handle "MM:SS" format
                            if ":" in min_str:
                                parts = min_str.split(":")
                                if len(parts) >= 2:
                                    minutes = float(parts[0]) + (float(parts[1]) / 60.0)
                                elif len(parts) == 1:
                                    minutes = float(parts[0])
                            else:
                                # Try to parse as float directly
                                minutes = float(min_str)
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                "Failed to parse minutes",
                                player_id=player_id,
                                game_id=str(row.get("Game_ID")),
                                raw_value=min_str,
                                column=min_col_found,
                                error=str(e)
                            )
                            minutes = 0.0
                    else:
                        # Log when minutes column is not found
                        if idx == 0:  # Only log for first row to avoid spam
                            logger.warning(
                                "Minutes column not found in API response",
                                player_id=player_id,
                                available_columns=list(row.index),
                                checked_columns=["MIN", "MINUTES", "MP"]
                            )
                    
                    # Log first game's minutes parsing for debugging
                    if idx == 0:
                        logger.info(
                            "Minutes parsing result",
                            player_id=player_id,
                            game_id=str(row.get("Game_ID")),
                            raw_value=min_str,
                            column_found=min_col_found,
                            parsed_minutes=minutes
                        )
                    
                    items.append({
                        "game_id": str(row.get("Game_ID")),
                        "game_date": str(row.get("GAME_DATE")),
                        "matchup": str(row.get("MATCHUP")),
                        "pts": float(row.get("PTS", 0) or 0),
                        "reb": float(row.get("REB", 0) or 0),
                        "ast": float(row.get("AST", 0) or 0),
                        "tpm": float(row.get("FG3M", 0) or 0),
                        "minutes": minutes,
                    })
                
                # Log summary of parsed minutes
                minutes_list = [item["minutes"] for item in items]
                valid_minutes = [m for m in minutes_list if m > 0]
                logger.info(
                    "Player game log parsing complete",
                    player_id=player_id,
                    total_games=len(items),
                    games_with_minutes=len(valid_minutes),
                    avg_minutes=sum(valid_minutes) / len(valid_minutes) if valid_minutes else 0.0,
                    sample_minutes=minutes_list[:5] if minutes_list else []
                )
                
                return items
            except Exception as e:
                error_str = str(e)
                is_timeout = "timeout" in error_str.lower() or "Read timed out" in error_str
                
                if is_timeout and attempt < max_retries - 1:
                    # Exponential backoff: 2s, 4s, 8s
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "Player game log request timed out, retrying",
                        player_id=player_id,
                        season=season_to_use,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=delay,
                        error=error_str
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed or non-timeout error
                    logger.warning(
                        "Failed to fetch player game log",
                        player_id=player_id,
                        season=season_to_use,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        error=error_str
                    )
                    return []
    
    @staticmethod
    def search_players(query: str) -> List[Dict[str, Any]]:
        """
        Search for players by name. Uses fetch_all_players_including_rookies for comprehensive results.
        
        Args:
            query: Search query string
            
        Returns:
            List of player dictionaries with id, name, and team (limited to 20 results)
        """
        all_players = NBADataService.fetch_all_players_including_rookies()
        query_lower = query.lower()
        # Get team mapping for abbreviation conversion
        teams = NBADataService.fetch_all_teams()
        team_map = {t.get("id"): t.get("abbreviation") for t in teams if t.get("id") and t.get("abbreviation")}
        
        matches = []
        for p in all_players:
            if p.get("full_name") and query_lower in p.get("full_name", "").lower():
                team_id = p.get("team_id")
                team_abbr = team_map.get(team_id) if team_id else None
                matches.append({
                    "id": int(p.get("id")),
                    "name": p.get("full_name"),
                    "team": team_abbr  # Convert team_id to abbreviation string
                })
        return matches[:20]
    
    @staticmethod
    def fetch_player_game_log(player_id: int, season: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch player game log with 24-hour caching.
        
        Args:
            player_id: NBA player ID
            season: Season string (e.g., "2025-26"), defaults to current season
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of game log entries
        """
        if force_refresh:
            return NBADataService._fetch_player_game_log_impl(player_id, season)
        
        # Use cached version with date-based key for daily invalidation
        cache = get_cache_service()
        season_to_use = season or "2025-26"
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:player_game_log:{player_id}:{season_to_use}:{today_str}"
        
        # Check cache manually since we need conditional caching
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Fetch and cache
        result = NBADataService._fetch_player_game_log_impl(player_id, season)
        cache.set(cache_key, result, ttl=86400)
        return result

    @staticmethod
    def fetch_todays_games() -> List[Dict[str, Any]]:
        """
        Fetch all games for today, including:
        - Scheduled games (not yet started)
        - Live games (in progress)
        - Recently completed games (finished today)
        
        Uses scoreboardv2 for scheduled games and live scoreboard for live/completed games.
        Filters games by their Eastern Time date to ensure we only get today's games.
        Cached for 24 hours with date-based key for automatic daily invalidation.
        
        Note: After fetching, checks for finished games and invalidates player log caches
        for players in those games to ensure fresh data.
        Uses CacheService (Redis/SQLite) for persistence across container restarts.
        """
        cache = get_cache_service()
        import pytz
        
        # Get today's date in Eastern Time (NBA's primary timezone)
        et_tz = pytz.timezone('America/New_York')
        today_et = datetime.now(et_tz).date()
        today_str = today_et.isoformat()
        cache_key = f"nba_api:todays_games:{today_str}"
        date_str = today_et.strftime('%m/%d/%Y')
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        games = []
        
        # First, try to get scheduled games from scoreboardv2 (stats endpoint)
        # We need to work around the WinProbability KeyError for scheduled games
        if scoreboardv2 is not None:
            try:
                # Make direct API call to avoid WinProbability issue
                import httpx
                url = f"https://stats.nba.com/stats/scoreboardV2"
                params = {
                    "GameDate": date_str,
                    "LeagueID": "00",
                    "DayOffset": "0"
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": "https://www.nba.com/",
                    "Accept": "application/json"
                }
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        result_sets = data.get("resultSets", [])
                        
                        # Find game_header result set
                        game_header_data = None
                        for rs in result_sets:
                            if rs.get("name") == "GameHeader":
                                game_header_data = rs
                                break
                        
                        if game_header_data:
                            headers_list = game_header_data.get("headers", [])
                            rows = game_header_data.get("rowSet", [])
                            
                            # Get team mappings
                            teams = NBADataService.fetch_all_teams() or []
                            team_id_to_abbr = {t.get("id"): t.get("abbreviation") for t in teams}
                            
                            # Map header indices
                            try:
                                home_team_idx = headers_list.index("HOME_TEAM_ID")
                                away_team_idx = headers_list.index("VISITOR_TEAM_ID")
                                game_time_idx = headers_list.index("GAME_TIME_ET")
                                game_id_idx = headers_list.index("GAME_ID")
                                status_idx = headers_list.index("GAME_STATUS_ID")
                            except ValueError:
                                # Fallback to common indices
                                home_team_idx = 6
                                away_team_idx = 7
                                game_time_idx = 4
                                game_id_idx = 2
                                status_idx = 3
                            
                            for row in rows:
                                try:
                                    home_team_id = row[home_team_idx] if home_team_idx < len(row) else None
                                    away_team_id = row[away_team_idx] if away_team_idx < len(row) else None
                                    game_time_et = row[game_time_idx] if game_time_idx < len(row) else ""
                                    game_id = row[game_id_idx] if game_id_idx < len(row) else ""
                                    game_status_id = row[status_idx] if status_idx < len(row) else 1
                                    
                                    home_abbr = team_id_to_abbr.get(home_team_id, f"TEAM{home_team_id}")
                                    away_abbr = team_id_to_abbr.get(away_team_id, f"TEAM{away_team_id}")
                                    
                                    # Determine status
                                    game_status = "SCHEDULED"
                                    if game_status_id == 2:
                                        game_status = "LIVE"
                                    elif game_status_id == 3:
                                        game_status = "FINAL"
                                    
                                    # Build ET time string
                                    game_et_str = None
                                    if game_time_et:
                                        try:
                                            time_str = str(game_time_et).strip()
                                            time_upper = time_str.upper()
                                            
                                            # Remove "ET" suffix if present
                                            time_clean = time_upper.replace(" ET", "").replace("ET", "").strip()
                                            
                                            # Handle formats like "7:00 PM", "19:00", "7:00 pm"
                                            if "PM" in time_clean or "AM" in time_clean:
                                                # Parse 12-hour format
                                                time_part = time_clean.replace("PM", "").replace("AM", "").strip()
                                                time_parts = time_part.split(":")
                                                if len(time_parts) >= 2:
                                                    hour = int(time_parts[0])
                                                    minute = int(time_parts[1])
                                                    if "PM" in time_clean and hour != 12:
                                                        hour += 12
                                                    elif "AM" in time_clean and hour == 12:
                                                        hour = 0
                                                    et_dt = et_tz.localize(datetime.combine(today_et, datetime.min.time().replace(hour=hour, minute=minute)))
                                                    game_et_str = et_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                                            else:
                                                # Parse 24-hour format
                                                time_parts = time_clean.split(":")
                                                if len(time_parts) >= 2:
                                                    hour = int(time_parts[0])
                                                    minute = int(time_parts[1])
                                                    et_dt = et_tz.localize(datetime.combine(today_et, datetime.min.time().replace(hour=hour, minute=minute)))
                                                    game_et_str = et_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                                        except Exception as parse_error:
                                            # If parsing fails, create a basic ET string
                                            game_et_str = f"{today_et}T19:00:00-05:00"  # Default to 7 PM ET
                                    
                                    games.append({
                                        "gameId": str(game_id),
                                        "home": home_abbr,
                                        "away": away_abbr,
                                        "gameTimeUTC": None,
                                        "gameEt": game_et_str or f"{today_et}T{game_time_et}:00-05:00",
                                        "status": game_status,
                                    })
                                except (IndexError, ValueError, TypeError) as e:
                                    continue
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("ScoreboardV2 API call failed", error=str(e))
        
        # Also check live scoreboard for live/completed games
        if scoreboard is not None:
            try:
                sb = scoreboard.ScoreBoard()
                for g in sb.games.get_dict():
                    game_et = g.get("gameEt")
                    game_status = g.get("gameStatusText", "").upper()
                    game_id = g.get("gameId")
                    
                    # Filter by game date in Eastern Time
                    game_date_et = None
                    if game_et:
                        try:
                            et_dt = datetime.fromisoformat(game_et.replace('Z', '+00:00'))
                            game_date_et = et_dt.astimezone(et_tz).date()
                        except (ValueError, AttributeError):
                            game_time_utc = g.get("gameTimeUTC")
                            if game_time_utc:
                                try:
                                    utc_dt = datetime.fromisoformat(game_time_utc.replace('Z', '+00:00'))
                                    game_date_et = utc_dt.astimezone(et_tz).date()
                                except (ValueError, AttributeError):
                                    pass
                    
                    # Only include games for today that we haven't already added
                    if game_date_et and game_date_et == today_et:
                        existing_game_ids = {g.get("gameId") for g in games}
                        if str(game_id) not in existing_game_ids:
                            games.append({
                                "gameId": str(game_id),
                                "home": g.get("homeTeam", {}).get("teamTricode"),
                                "away": g.get("awayTeam", {}).get("teamTricode"),
                                "gameTimeUTC": g.get("gameTimeUTC"),
                                "gameEt": game_et,
                                "status": game_status,
                            })
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("Live scoreboard failed", error=str(e))
        
        # Note: Game status monitoring for cache invalidation is handled separately
        # via GameStatusMonitor.check_and_invalidate_finished_games() which can be
        # called periodically or via admin endpoint POST /api/v1/admin/cache/refresh/player-logs
        
        # Cache for 24 hours
        cache.set(cache_key, games, ttl=86400)
        return games
    
    @staticmethod
    def fetch_games_for_date(target_date) -> List[Dict[str, Any]]:
        """
        Fetch games for a specific date. Uses scoreboardv2 for scheduled games.
        Filters games by their Eastern Time date to ensure accuracy.
        """
        from datetime import datetime
        import pytz
        
        # Convert target_date to date object if it's a string
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        
        et_tz = pytz.timezone('America/New_York')
        date_str = target_date.strftime('%m/%d/%Y')
        
        games = []
        
        # Use scoreboardv2 to get scheduled games for the specific date
        if scoreboardv2 is not None:
            try:
                import httpx
                url = "https://stats.nba.com/stats/scoreboardV2"
                params = {
                    "GameDate": date_str,
                    "LeagueID": "00",
                    "DayOffset": "0"
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": "https://www.nba.com/",
                    "Accept": "application/json"
                }
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(url, params=params, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        result_sets = data.get("resultSets", [])
                        
                        game_header_data = None
                        for rs in result_sets:
                            if rs.get("name") == "GameHeader":
                                game_header_data = rs
                                break
                        
                        if game_header_data:
                            headers_list = game_header_data.get("headers", [])
                            rows = game_header_data.get("rowSet", [])
                            
                            teams = NBADataService.fetch_all_teams() or []
                            team_id_to_abbr = {t.get("id"): t.get("abbreviation") for t in teams}
                            
                            try:
                                home_team_idx = headers_list.index("HOME_TEAM_ID")
                                away_team_idx = headers_list.index("VISITOR_TEAM_ID")
                                game_time_idx = headers_list.index("GAME_TIME_ET")
                                game_id_idx = headers_list.index("GAME_ID")
                                status_idx = headers_list.index("GAME_STATUS_ID")
                            except ValueError:
                                home_team_idx = 6
                                away_team_idx = 7
                                game_time_idx = 4
                                game_id_idx = 2
                                status_idx = 3
                            
                            for row in rows:
                                try:
                                    home_team_id = row[home_team_idx] if home_team_idx < len(row) else None
                                    away_team_id = row[away_team_idx] if away_team_idx < len(row) else None
                                    game_time_et = row[game_time_idx] if game_time_idx < len(row) else ""
                                    game_id = row[game_id_idx] if game_id_idx < len(row) else ""
                                    game_status_id = row[status_idx] if status_idx < len(row) else 1
                                    
                                    home_abbr = team_id_to_abbr.get(home_team_id, f"TEAM{home_team_id}")
                                    away_abbr = team_id_to_abbr.get(away_team_id, f"TEAM{away_team_id}")
                                    
                                    game_status = "SCHEDULED"
                                    if game_status_id == 2:
                                        game_status = "LIVE"
                                    elif game_status_id == 3:
                                        game_status = "FINAL"
                                    
                                    game_et_str = None
                                    if game_time_et:
                                        try:
                                            time_str = str(game_time_et).strip()
                                            time_upper = time_str.upper()
                                            time_clean = time_upper.replace(" ET", "").replace("ET", "").strip()
                                            
                                            if "PM" in time_clean or "AM" in time_clean:
                                                time_part = time_clean.replace("PM", "").replace("AM", "").strip()
                                                time_parts = time_part.split(":")
                                                if len(time_parts) >= 2:
                                                    hour = int(time_parts[0])
                                                    minute = int(time_parts[1])
                                                    if "PM" in time_clean and hour != 12:
                                                        hour += 12
                                                    elif "AM" in time_clean and hour == 12:
                                                        hour = 0
                                                    et_dt = et_tz.localize(datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute)))
                                                    game_et_str = et_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                                            else:
                                                time_parts = time_clean.split(":")
                                                if len(time_parts) >= 2:
                                                    hour = int(time_parts[0])
                                                    minute = int(time_parts[1])
                                                    et_dt = et_tz.localize(datetime.combine(target_date, datetime.min.time().replace(hour=hour, minute=minute)))
                                                    game_et_str = et_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                                        except Exception:
                                            game_et_str = f"{target_date}T19:00:00-05:00"
                                    
                                    games.append({
                                        "gameId": str(game_id),
                                        "home": home_abbr,
                                        "away": away_abbr,
                                        "gameTimeUTC": None,
                                        "gameEt": game_et_str or f"{target_date}T{game_time_et}:00-05:00",
                                        "status": game_status,
                                    })
                                except (IndexError, ValueError, TypeError):
                                    continue
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("ScoreboardV2 API call failed for date", date=str(target_date), error=str(e))
        
        # Also check live scoreboard for live/completed games on that date
        if scoreboard is not None:
            try:
                sb = scoreboard.ScoreBoard()
                for g in sb.games.get_dict():
                    game_et = g.get("gameEt")
                    game_status = g.get("gameStatusText", "").upper()
                    game_id = g.get("gameId")
                    
                    game_date_et = None
                    if game_et:
                        try:
                            et_dt = datetime.fromisoformat(game_et.replace('Z', '+00:00'))
                            game_date_et = et_dt.astimezone(et_tz).date()
                        except (ValueError, AttributeError):
                            game_time_utc = g.get("gameTimeUTC")
                            if game_time_utc:
                                try:
                                    utc_dt = datetime.fromisoformat(game_time_utc.replace('Z', '+00:00'))
                                    game_date_et = utc_dt.astimezone(et_tz).date()
                                except (ValueError, AttributeError):
                                    pass
                    
                    if game_date_et and game_date_et == target_date:
                        existing_game_ids = {g.get("gameId") for g in games}
                        if str(game_id) not in existing_game_ids:
                            games.append({
                                "gameId": str(game_id),
                                "home": g.get("homeTeam", {}).get("teamTricode"),
                                "away": g.get("awayTeam", {}).get("teamTricode"),
                                "gameTimeUTC": g.get("gameTimeUTC"),
                                "gameEt": game_et,
                                "status": game_status,
                            })
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("Live scoreboard failed for date", date=str(target_date), error=str(e))
        
        return games
