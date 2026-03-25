from __future__ import annotations
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..services.cache_service import get_cache_service
from ..utils.season import get_current_season


def _load_rookie_merge_list() -> List[Dict[str, Any]]:
    """Load curated list of rookies (full_name, nba_id, team_abbr) not yet in nba_api static data."""
    try:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(app_dir, "data", "rookie_merge.json")
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _clean_player_name(name: str) -> str:
    """Clean a player name for display: strip, collapse spaces, normalize Jr./Sr./II/III/IV spacing.
    Only applied to recent (rostered) players."""
    if not name or not isinstance(name, str):
        return name
    s = name.strip()
    if not s:
        return name
    # Collapse multiple spaces/newlines/tabs to single space
    s = re.sub(r"\s+", " ", s)
    # Ensure one space before common suffixes (Jr., Sr., II, III, IV)
    s = re.sub(r"\s*(Jr\.?|Sr\.?|II|III|IV)\s*$", r" \1", s, flags=re.IGNORECASE)
    return s.strip()

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
            # Cap NBA API timeout at 60s so player game log cascade (ESPN first) can complete within proxy limits
            # This patches both direct requests and Session objects used by nba_api
            try:
                original_get = requests.get
                original_post = requests.post
                
                def patched_get(*args, **kwargs):
                    # 60s timeout so cascade (ESPN first, then NBA) can finish within proxy limits
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = 60.0
                    elif isinstance(kwargs['timeout'], (int, float)) and kwargs['timeout'] > 60:
                        kwargs['timeout'] = 60.0
                    return original_get(*args, **kwargs)
                
                def patched_post(*args, **kwargs):
                    if 'timeout' not in kwargs:
                        kwargs['timeout'] = 60.0
                    elif isinstance(kwargs['timeout'], (int, float)) and kwargs['timeout'] > 60:
                        kwargs['timeout'] = 60.0
                    return original_post(*args, **kwargs)
                
                # Patch requests methods used by nba_api
                requests.get = patched_get
                requests.post = patched_post
                
                # Also patch Session.request if available
                if hasattr(requests, 'Session') and hasattr(requests.Session, 'request'):
                    original_session_request = requests.Session.request
                    
                    def patched_session_request(self, method, url, **kwargs):
                        if 'timeout' not in kwargs:
                            kwargs['timeout'] = 60.0
                        elif isinstance(kwargs['timeout'], (int, float)) and kwargs['timeout'] > 60:
                            kwargs['timeout'] = 60.0
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
    # ESPN abbreviation -> NBA team ID (used for teams fallback and roster mapping)
    ESPN_ABBR_TO_NBA_ID: Dict[str, int] = {
        "ATL": 1610612737, "BOS": 1610612738, "BKN": 1610612751,
        "CHA": 1610612766, "CHI": 1610612741, "CLE": 1610612739,
        "DAL": 1610612742, "DEN": 1610612743, "DET": 1610612765,
        "GS": 1610612744, "GSW": 1610612744,
        "HOU": 1610612745, "IND": 1610612754,
        "LAC": 1610612746, "LAL": 1610612747, "MEM": 1610612763,
        "MIA": 1610612748, "MIL": 1610612749, "MIN": 1610612750,
        "NO": 1610612740, "NOP": 1610612740,
        "NY": 1610612752, "NYK": 1610612752,
        "OKC": 1610612760, "ORL": 1610612753,
        "PHI": 1610612755, "PHX": 1610612756,
        "POR": 1610612757, "SAC": 1610612758,
        "SA": 1610612759, "SAS": 1610612759,
        "TOR": 1610612761,
        "UTAH": 1610612762, "UTA": 1610612762,
        "WSH": 1610612764, "WAS": 1610612764,
    }

    @staticmethod
    def fetch_all_teams() -> List[Dict[str, Any]]:
        """
        Fetch all NBA teams. Cached for 24 hours with date-based key for daily invalidation.
        Uses NBA API static data when available; falls back to ESPN so team pages always have data.
        """
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:teams:{today_str}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        result: List[Dict[str, Any]] = []
        if static_teams is not None:
            result = static_teams.get_teams()
        
        # Fallback to ESPN when NBA static teams unavailable or empty (e.g. in Docker without nba_api)
        if not result:
            try:
                import requests as _req
                resp = _req.get(
                    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
                    timeout=15,
                )
                data = resp.json()
                espn_teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
                for t in espn_teams:
                    td = t.get("team", {})
                    abbr = (td.get("abbreviation") or "").strip().upper()
                    nba_id = NBADataService.ESPN_ABBR_TO_NBA_ID.get(abbr)
                    if nba_id is None:
                        continue
                    result.append({
                        "id": nba_id,
                        "full_name": td.get("displayName") or td.get("name") or "",
                        "abbreviation": abbr,
                        "city": td.get("location") or td.get("nickname") or "",
                        "nickname": td.get("nickname") or td.get("shortDisplayName") or "",
                        "conference": None,
                        "division": None,
                    })
            except Exception:
                pass
        
        if result:
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
        When CommonAllPlayers is unreachable, enriches static players with team_id
        by fetching rosters from ESPN (which is faster and more reliable).
        Cached for 24 hours with date-based key for daily invalidation.
        Uses CacheService (Redis/SQLite) for persistence across container restarts."""
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:players_all_including_rookies:{today_str}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # Quick sanity check: if cached data has zero players with team_id,
            # the cache is stale/broken — refetch.
            has_teams = any(p.get("team_id") and p.get("team_id") != 0 for p in cached_data[:200])
            if has_teams:
                return cached_data

        all_players: List[Dict[str, Any]] = []

        # Strategy 1: CommonAllPlayers (NBA API) — has team_id but unreliable
        if commonallplayers is not None:
            try:
                cap = commonallplayers.CommonAllPlayers(
                    is_only_current_season=1,
                    timeout=10,
                )
                data = cap.get_dict()
                result_sets = data.get("resultSets", [])
                if result_sets:
                    headers = result_sets[0].get("headers", [])
                    rows = result_sets[0].get("rowSet", [])
                    try:
                        person_id_idx = headers.index("PERSON_ID")
                        display_first_last_idx = headers.index("DISPLAY_FIRST_LAST")
                        team_id_idx = headers.index("TEAM_ID")
                        roster_status_idx = headers.index("ROSTERSTATUS") if "ROSTERSTATUS" in headers else None
                        position_idx = headers.index("POSITION") if "POSITION" in headers else None
                        jersey_idx = headers.index("JERSEY") if "JERSEY" in headers else None
                    except ValueError:
                        person_id_idx, display_first_last_idx, team_id_idx = 0, 2, 8
                        roster_status_idx, position_idx, jersey_idx = 3, None, None

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
                                    "jersey_number": jersey_number,
                                })
            except Exception:
                pass

        # Check how many players actually got a team_id from CommonAllPlayers
        players_with_team = sum(1 for p in all_players if p.get("team_id") and p.get("team_id") != 0)

        # Strategy 2: ESPN rosters — used to enrich team_id and to add current-roster-only players
        # (rookies, 2–3 year players) without pulling in 1900s/historical from static.
        espn_name_to_nba_team: Dict[str, int] = {}
        espn_name_to_pos: Dict[str, str] = {}
        espn_name_to_nba_team, espn_name_to_pos = NBADataService._fetch_espn_roster_mapping()

        # Merge static players and enrich with ESPN team_id where needed.
        # Only add current-roster players: never add full static list (contains 1900s/historical).
        if static_players is not None:
            static_players_list = static_players.get_players()
            static_players_by_id = {p.get("id"): p for p in static_players_list}
            # Name → static player for matching ESPN names to NBA ids (lowercase full_name)
            static_by_name_lower: Dict[str, Dict[str, Any]] = {}
            for p in static_players_list:
                fn = (p.get("full_name") or "").strip().lower()
                if fn and fn not in static_by_name_lower:
                    static_by_name_lower[fn] = p

            # Enrich existing players from CommonAllPlayers
            for player in all_players:
                pid = player.get("id")
                if pid in static_players_by_id:
                    sp = static_players_by_id[pid]
                    if not player.get("position") and sp.get("position"):
                        player["position"] = sp["position"]
                    if not player.get("jersey_number") and sp.get("jersey_number"):
                        player["jersey_number"] = sp["jersey_number"]
                # If still no team_id, try ESPN mapping by name
                if (not player.get("team_id") or player.get("team_id") == 0) and espn_name_to_nba_team:
                    name_key = (player.get("full_name") or "").strip().lower()
                    if name_key in espn_name_to_nba_team:
                        player["team_id"] = espn_name_to_nba_team[name_key]
                        player["is_active"] = True
                        if not player.get("position") and name_key in espn_name_to_pos:
                            player["position"] = espn_name_to_pos[name_key]

            # Only add players who are on current rosters (ESPN), never the full static list.
            # That avoids 1900s/historical players; ESPN + static name match adds rookies and
            # 2–3 year players who may be missing from CommonAllPlayers.
            existing_ids = {p.get("id") for p in all_players}
            for name_key, team_id in espn_name_to_nba_team.items():
                sp = static_by_name_lower.get(name_key)
                if sp and sp.get("id") not in existing_ids:
                    enriched = {
                        "id": sp.get("id"),
                        "full_name": sp.get("full_name", ""),
                        "first_name": sp.get("first_name", ""),
                        "last_name": sp.get("last_name", ""),
                        "team_id": team_id,
                        "is_active": True,
                        "position": espn_name_to_pos.get(name_key) or sp.get("position"),
                        "jersey_number": sp.get("jersey_number"),
                    }
                    all_players.append(enriched)
                    existing_ids.add(sp.get("id"))

        # Strategy 3: Curated merge — rookies on NBA.com/ESPN not yet in static_players
        existing_ids = {p.get("id") for p in all_players}
        try:
            for entry in _load_rookie_merge_list():
                try:
                    raw_id = entry.get("nba_id")
                    nba_id = int(raw_id) if raw_id is not None else None
                except (TypeError, ValueError):
                    nba_id = None
                full_name = (entry.get("full_name") or "").strip()
                if not nba_id or not full_name or nba_id in existing_ids:
                    continue
                team_abbr = (entry.get("team_abbr") or "").strip().upper()
                team_id = NBADataService.ESPN_ABBR_TO_NBA_ID.get(team_abbr) if team_abbr else None
                if team_id is None and espn_name_to_nba_team:
                    team_id = espn_name_to_nba_team.get(full_name.lower())
                name_parts = full_name.split()
                all_players.append({
                    "id": nba_id,
                    "full_name": full_name,
                    "first_name": name_parts[0] if name_parts else "",
                    "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                    "team_id": team_id,
                    "is_active": True,
                    "position": espn_name_to_pos.get(full_name.lower()) if espn_name_to_pos else None,
                    "jersey_number": None,
                })
                existing_ids.add(nba_id)
        except Exception:
            pass  # Don't break the whole player list if merge fails

        # Clean names for recent players only (on a team this year / current roster)
        for p in all_players:
            tid = p.get("team_id")
            if tid is not None and tid != 0:
                fn = p.get("full_name") or ""
                if fn:
                    cleaned = _clean_player_name(fn)
                    p["full_name"] = cleaned
                    parts = cleaned.split()
                    if len(parts) >= 2:
                        p["first_name"] = parts[0]
                        p["last_name"] = " ".join(parts[1:])
                    elif len(parts) == 1:
                        p["first_name"] = parts[0]
                        p["last_name"] = ""

        cache.set(cache_key, all_players, ttl=86400)
        return all_players

    @staticmethod
    def _fetch_espn_roster_mapping() -> tuple:
        """Fetch all 30 NBA team rosters from ESPN and build a
        lowercase-name → nba_team_id mapping plus name → position mapping.
        ESPN is fast and reliable even when stats.nba.com is down."""
        import requests as _req

        name_to_team: Dict[str, int] = {}
        name_to_pos: Dict[str, str] = {}

        try:
            teams_resp = _req.get(
                "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
                timeout=15,
            )
            teams_data = teams_resp.json()
            espn_teams = teams_data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])

            for t in espn_teams:
                td = t.get("team", {})
                espn_team_id = td.get("id", "")
                espn_abbr = (td.get("abbreviation") or "").upper()

                nba_team_id = NBADataService.ESPN_ABBR_TO_NBA_ID.get(espn_abbr)
                if not nba_team_id:
                    continue

                try:
                    roster_resp = _req.get(
                        f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{espn_team_id}/roster",
                        timeout=15,
                    )
                    roster_data = roster_resp.json()
                    athletes = roster_data.get("athletes", [])
                    for a in athletes:
                        name = (a.get("fullName") or a.get("displayName") or "").strip().lower()
                        if name:
                            name_to_team[name] = nba_team_id
                            pos = a.get("position", {})
                            if isinstance(pos, dict):
                                pos_abbr = pos.get("abbreviation", "")
                            else:
                                pos_abbr = str(pos)
                            if pos_abbr:
                                name_to_pos[name] = pos_abbr
                except Exception:
                    continue
        except Exception:
            pass

        return name_to_team, name_to_pos

    @staticmethod
    def _fetch_player_game_log_impl(player_id: int, season: Optional[str]) -> List[Dict[str, Any]]:
        """Internal implementation of fetch_player_game_log without caching.
        Includes retry logic with exponential backoff for handling timeouts."""
        if playergamelog is None:
            import structlog
            logger = structlog.get_logger()
            logger.error("NBA API playergamelog module not available - check nba_api installation")
            return []
        
        import structlog
        logger = structlog.get_logger()
        
        # Default to current season if not provided
        season_to_use = season or get_current_season()
        
        max_retries = 1
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                gl = playergamelog.PlayerGameLog(player_id=player_id, season=season_to_use, timeout=5)
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
                        "fga": float(row.get("FGA", 0) or 0),
                        "fta": float(row.get("FTA", 0) or 0),
                        "tov": float(row.get("TOV", 0) or 0),
                        "oreb": float(row.get("OREB", 0) or 0),
                        "stl": float(row.get("STL", 0) or 0),
                        "blk": float(row.get("BLK", 0) or 0),
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
        # Build team map with normalized int keys so lookup works (cache may store id as int or str)
        teams = NBADataService.fetch_all_teams() or []
        team_map: Dict[Any, str] = {}
        for t in teams:
            tid, abbr = t.get("id"), t.get("abbreviation")
            if tid is not None and abbr:
                try:
                    team_map[int(tid)] = abbr
                except (TypeError, ValueError):
                    pass
        
        def _team_abbr_for_player(p: Dict[str, Any]) -> Optional[str]:
            # Prefer explicit abbreviation on player (e.g. from static merge)
            abbr = p.get("team_abbreviation") or p.get("team")
            if abbr and isinstance(abbr, str):
                return abbr
            # Resolve team_id to abbreviation (normalize to int for lookup)
            team_id = p.get("team_id")
            if team_id is None:
                return None
            try:
                return team_map.get(int(team_id))
            except (TypeError, ValueError):
                return None
        
        matches = []
        for p in all_players:
            if p.get("full_name") and query_lower in p.get("full_name", "").lower():
                team_abbr = _team_abbr_for_player(p)
                matches.append({
                    "id": int(p.get("id")),
                    "name": p.get("full_name"),
                    "team": team_abbr
                })
        return matches[:20]

    @staticmethod
    def _is_good_game_log(result: Optional[List[Dict[str, Any]]], min_games: int = 1) -> bool:
        """
        Return True if result is a non-empty list of valid game log entries.
        Valid entries must have: game_id, game_date, matchup, pts, reb, ast.
        """
        if result is None or len(result) < min_games:
            return False
        required = ("game_id", "game_date", "matchup", "pts", "reb", "ast")
        for entry in result:
            if not isinstance(entry, dict):
                return False
            for key in required:
                if key not in entry:
                    return False
        return True
    
    @staticmethod
    def _persist_game_log_to_db(player_id: int, season: str, data: List[Dict[str, Any]]) -> None:
        """Upsert a player's game log rows into player_game_log_cache (best-effort, never raises)."""
        if not data:
            return
        try:
            from ..database import SessionLocal
            from ..models.player_game_log_cache import PlayerGameLogCache
            db = SessionLocal()
            try:
                # Replace all rows for this player+season — clean and simple
                db.query(PlayerGameLogCache).filter_by(
                    player_id=player_id, season=season
                ).delete(synchronize_session=False)
                for row in data:
                    db.add(PlayerGameLogCache(
                        player_id=player_id,
                        season=season,
                        game_id=str(row.get("game_id", "")),
                        game_date=str(row.get("game_date", "")),
                        matchup=str(row.get("matchup", "")),
                        pts=float(row.get("pts", 0) or 0),
                        reb=float(row.get("reb", 0) or 0),
                        ast=float(row.get("ast", 0) or 0),
                        tpm=float(row.get("tpm", 0) or 0),
                        minutes=float(row.get("minutes", 0) or 0),
                        fga=float(row.get("fga", 0) or 0),
                        fta=float(row.get("fta", 0) or 0),
                        tov=float(row.get("tov", 0) or 0),
                        oreb=float(row.get("oreb", 0) or 0),
                        stl=float(row.get("stl", 0) or 0),
                        blk=float(row.get("blk", 0) or 0),
                    ))
                db.commit()
            finally:
                db.close()
        except Exception:
            pass  # DB persistence is best-effort; never break the main flow

    @staticmethod
    def _get_game_log_from_db(player_id: int, season: str) -> List[Dict[str, Any]]:
        """Read a player's game log from the DB cache (fallback when Redis is cold)."""
        try:
            from ..database import SessionLocal
            from ..models.player_game_log_cache import PlayerGameLogCache
            db = SessionLocal()
            try:
                rows = (
                    db.query(PlayerGameLogCache)
                    .filter_by(player_id=player_id, season=season)
                    .order_by(PlayerGameLogCache.game_date.desc())
                    .all()
                )
                return [r.to_dict() for r in rows] if rows else []
            finally:
                db.close()
        except Exception:
            return []

    @staticmethod
    def fetch_player_game_log(player_id: int, season: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch player game log with 24-hour Redis caching + DB persistence.
        Read order: Redis → DB → ESPN → NBA API.
        On any fresh fetch from the external APIs, results are written to both Redis and the DB.
        Good data = non-empty list with valid entries (game_id, game_date, matchup, pts, reb, ast).
        """
        import structlog
        log = structlog.get_logger()
        season_to_use = season or get_current_season()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:player_game_log:{player_id}:{season_to_use}:{today_str}"
        cache = get_cache_service()

        if not force_refresh:
            # 1. Redis (fastest)
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # 2. DB fallback — no API call needed, re-warm Redis while we're here
            db_data = NBADataService._get_game_log_from_db(player_id, season_to_use)
            if db_data:
                log.debug("Player game log from DB cache", player_id=player_id, count=len(db_data))
                cache.set(cache_key, db_data, ttl=86400)
                return db_data

        def _store(result: List[Dict[str, Any]]) -> None:
            """Write to Redis + DB in one call."""
            cache.set(cache_key, result, ttl=86400)
            NBADataService._persist_game_log_to_db(player_id, season_to_use, result)

        def try_nba_api() -> List[Dict[str, Any]]:
            return NBADataService._fetch_player_game_log_impl(player_id, season)

        def try_espn() -> List[Dict[str, Any]]:
            try:
                from .espn_game_log import fetch_player_game_log_espn
                return fetch_player_game_log_espn(player_id, season, limit=25)
            except Exception as e:
                log.warning("ESPN game log attempt failed", player_id=player_id, error=str(e))
                return []

        attempts: List[List[Dict[str, Any]]] = []

        # Try ESPN first (usually faster); then NBA API. Avoids 2+ min wait when NBA API is slow.
        # Step 1: ESPN
        r1 = try_espn()
        attempts.append(r1 or [])
        if NBADataService._is_good_game_log(r1):
            log.info("Player game log from espn", player_id=player_id, count=len(r1))
            _store(r1)
            return r1

        # Step 2: nba_api (single attempt — skip if stats.nba.com is unreachable)
        r2 = try_nba_api()
        attempts.append(r2 or [])
        if NBADataService._is_good_game_log(r2):
            log.info("Player game log from nba_api", player_id=player_id, count=len(r2))
            _store(r2)
            return r2

        # Step 3: retry ESPN (no more NBA API retries — they just burn time)
        r3 = try_espn()
        attempts.append(r3 or [])
        if NBADataService._is_good_game_log(r3):
            log.info("Player game log from espn_retry", player_id=player_id, count=len(r3))
            _store(r3)
            return r3

        best = max(attempts, key=len) if attempts else []
        if not best:
            log.warning("No good game log data after cascade", player_id=player_id)
        else:
            log.info("Player game log best of cascade", player_id=player_id, count=len(best))
        _store(best)
        return best

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
                
                with httpx.Client(timeout=30.0) as client:
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
        
        # ESPN fallback: when NBA API returns no games (e.g. blocked on VPS, rate limit, or empty),
        # use ESPN scoreboard so top-picks and daily props still get today's games.
        if not games:
            try:
                from .espn_api_service import get_espn_service
                espn = get_espn_service()
                espn_date_str = today_et.strftime("%Y%m%d")
                scoreboard_data = espn.get_scoreboard(date=espn_date_str)
                if scoreboard_data and isinstance(scoreboard_data.get("events"), list):
                    for event in scoreboard_data["events"]:
                        try:
                            comps = event.get("competitions") or []
                            home_abbr = away_abbr = None
                            for comp in comps:
                                for c in comp.get("competitors") or []:
                                    abbr = (c.get("team") or {}).get("abbreviation", "")
                                    if (c.get("homeAway") or "").lower() == "home":
                                        home_abbr = abbr
                                    else:
                                        away_abbr = abbr
                            if home_abbr and away_abbr:
                                status_obj = event.get("status") or {}
                                status_id = str(status_obj.get("id", "1"))
                                status_desc = (status_obj.get("description") or "").upper()
                                if status_id == "3" or "FINAL" in status_desc or status_obj.get("completed"):
                                    status = "FINAL"
                                elif status_id == "2" or "IN PROGRESS" in status_desc or "LIVE" in status_desc:
                                    status = "LIVE"
                                else:
                                    status = "SCHEDULED"
                                games.append({
                                    "gameId": str(event.get("id", "")),
                                    "home": home_abbr,
                                    "away": away_abbr,
                                    "gameTimeUTC": event.get("date"),
                                    "gameEt": event.get("date"),
                                    "status": status,
                                })
                        except (KeyError, TypeError, IndexError):
                            continue
                    if games:
                        import structlog
                        _log = structlog.get_logger()
                        _log.info("fetch_todays_games: using ESPN fallback", count=len(games), date=today_str)
            except Exception as e:
                import structlog
                _log = structlog.get_logger()
                _log.warning("ESPN fallback for todays_games failed", error=str(e))
        
        # Note: Game status monitoring for cache invalidation is handled separately
        # via GameStatusMonitor.check_and_invalidate_finished_games() which can be
        # called periodically or via admin endpoint POST /api/v1/admin/cache/refresh/player-logs
        
        # Cache for 24 hours only when we have games (do not cache empty list so next request can try ESPN fallback)
        if games:
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
                
                with httpx.Client(timeout=30.0) as client:
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
        
        # ESPN fallback when NBA API returns no games (e.g. blocked on VPS or empty)
        if not games:
            try:
                from .espn_api_service import get_espn_service
                espn = get_espn_service()
                espn_date_str = target_date.strftime("%Y%m%d")
                scoreboard_data = espn.get_scoreboard(date=espn_date_str)
                if scoreboard_data and isinstance(scoreboard_data.get("events"), list):
                    for event in scoreboard_data["events"]:
                        try:
                            comps = event.get("competitions") or []
                            home_abbr = away_abbr = None
                            for comp in comps:
                                for c in comp.get("competitors") or []:
                                    abbr = (c.get("team") or {}).get("abbreviation", "")
                                    if (c.get("homeAway") or "").lower() == "home":
                                        home_abbr = abbr
                                    else:
                                        away_abbr = abbr
                            if home_abbr and away_abbr:
                                status_obj = event.get("status") or {}
                                status_id = str(status_obj.get("id", "1"))
                                status_desc = (status_obj.get("description") or "").upper()
                                if status_id == "3" or "FINAL" in status_desc or status_obj.get("completed"):
                                    status = "FINAL"
                                elif status_id == "2" or "IN PROGRESS" in status_desc or "LIVE" in status_desc:
                                    status = "LIVE"
                                else:
                                    status = "SCHEDULED"
                                games.append({
                                    "gameId": str(event.get("id", "")),
                                    "home": home_abbr,
                                    "away": away_abbr,
                                    "gameTimeUTC": event.get("date"),
                                    "gameEt": event.get("date"),
                                    "status": status,
                                })
                        except (KeyError, TypeError, IndexError):
                            continue
                    if games:
                        import structlog
                        _log = structlog.get_logger()
                        _log.info("fetch_games_for_date: using ESPN fallback", date=str(target_date), count=len(games))
            except Exception as e:
                import structlog
                _log = structlog.get_logger()
                _log.warning("ESPN fallback for fetch_games_for_date failed", date=str(target_date), error=str(e))
        
        return games
