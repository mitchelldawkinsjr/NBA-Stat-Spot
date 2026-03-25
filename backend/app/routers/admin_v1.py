import os
from fastapi import APIRouter, Query, Depends, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.prop_scanner import PropScannerService
from ..models.players import Player
from ..services.nba_api_service import NBADataService, _clean_player_name
from ..services.daily_props_service import DailyPropsService
from ..services.high_hit_rate_service import HighHitRateService
from ..services.best_picks_service import BestPicksService
from ..services.settings_service import SettingsService
from ..services.data_integrity_service import DataIntegrityService
from ..services.game_status_monitor import GameStatusMonitor
from ..services.cache_service import get_cache_service
from ..services.external_api_rate_limiter import get_rate_limiter
from ..services.context_collector import ContextCollector
from ..services.game_prediction_service import get_game_prediction_service
from ..utils.season import get_current_season
from ..core.rate_limiter import limiter

def _require_admin(request: Request) -> None:
    """When ADMIN_SECRET is set, require matching header (Authorization: Bearer <secret> or X-Admin-Secret). When unset, allow access for backward compatibility."""
    secret = (os.getenv("ADMIN_SECRET") or "").strip()
    if not secret:
        return
    auth = request.headers.get("Authorization") or request.headers.get("X-Admin-Secret")
    token = None
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
    elif auth:
        token = auth.strip()
    if not token or token != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing admin credentials")


router = APIRouter(prefix="/api/v1/admin", tags=["admin_v1"], dependencies=[Depends(_require_admin)])

# Cache service instance
_cache = get_cache_service()

# Helper functions for cache operations (backward compatibility)
def _get_daily_props_cache(target_date: Optional[str] = None, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get daily props cache"""
    date_str = target_date or date.today().isoformat()
    cache_key = f"daily_props:{date_str}"
    if db:
        return _cache.get(cache_key, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.get(cache_key, db=db_session)
        finally:
            db_session.close()

def _set_daily_props_cache(data: Dict[str, Any], target_date: Optional[str] = None, ttl: int = 86400, db: Optional[Session] = None) -> bool:
    """Set daily props cache"""
    date_str = target_date or date.today().isoformat()
    cache_key = f"daily_props:{date_str}"
    if db:
        return _cache.set(cache_key, data, ttl=ttl, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.set(cache_key, data, ttl=ttl, db=db_session)
        finally:
            db_session.close()

def _get_high_hit_rate_cache(target_date: Optional[str] = None, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get high hit rate cache"""
    date_str = target_date or date.today().isoformat()
    cache_key = f"high_hit_rate:{date_str}"
    if db:
        return _cache.get(cache_key, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.get(cache_key, db=db_session)
        finally:
            db_session.close()

def _set_high_hit_rate_cache(data: Dict[str, Any], target_date: Optional[str] = None, ttl: int = 86400, db: Optional[Session] = None) -> bool:
    """Set high hit rate cache"""
    date_str = target_date or date.today().isoformat()
    cache_key = f"high_hit_rate:{date_str}"
    if db:
        return _cache.set(cache_key, data, ttl=ttl, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.set(cache_key, data, ttl=ttl, db=db_session)
        finally:
            db_session.close()

def _get_best_bets_cache(db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Get best bets cache"""
    cache_key = "best_bets:latest"
    if db:
        return _cache.get(cache_key, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.get(cache_key, db=db_session)
        finally:
            db_session.close()

def _set_best_bets_cache(data: List[Dict], ttl: int = 3600, db: Optional[Session] = None) -> bool:
    """Set best bets cache"""
    cache_key = "best_bets:latest"
    cache_data = {"results": data, "scanned_at": datetime.now().isoformat()}
    if db:
        return _cache.set(cache_key, cache_data, ttl=ttl, db=db)
    else:
        db_session = next(get_db())
        try:
            return _cache.set(cache_key, cache_data, ttl=ttl, db=db_session)
        finally:
            db_session.close()

def _is_cache_valid_for_date(target_date: Optional[str] = None) -> bool:
    """Check if cache exists for the given date"""
    date_str = target_date or date.today().isoformat()
    daily_props = _get_daily_props_cache(date_str)
    return daily_props is not None

# Backward compatibility: Export cache accessors for props_v1.py
_daily_props_cache = None  # Will be accessed via _get_daily_props_cache()
_daily_props_cache_date = None
_daily_props_cache_time = None
_high_hit_rate_cache = None
_high_hit_rate_cache_date = None
_high_hit_rate_cache_time = None
_best_bets_cache = []
_last_scan_time = None

def _is_cache_valid(cache_date: Optional[date], cache_time: Optional[datetime]) -> bool:
    """Check if cache is still valid (same day) - backward compatibility"""
    if not cache_date or not cache_time:
        return False
    today = date.today()
    return cache_date == today

def _clear_cache():
    """
    Clear all caches used by the dashboard, team data, and defensive/rank data.
    After this, the next request to any affected endpoint will repopulate from live sources.
    Call warm-dashboard after clear to prefill dashboard caches, or refresh the site.
    """
    db = next(get_db())
    total = 0
    try:
        patterns = [
            "daily_props:*",
            "high_hit_rate:*",
            "best_bets:*",
            "pick_of_the_day:*",
            "best_match_of_the_day:*",
            "top_picks:*",
            "hot_form:*",
            "game_predictions:*",
            "game_prediction_detail:*",
            "nba_api:todays_games:*",
            "stat_leaders:*",
            "defensive_ranks:*",
            "defensive_avgs:*",
            "offensive_ranks:*",
            "team_ranks_from_players_fallback:*",
            "pace_ranks:*",
            "position_def_ranks:*",
            "team_ppg_from_logs:*",
            "nba_api:teams:*",
            "team_stats:*",
        ]
        for pattern in patterns:
            total += _cache.clear_pattern(pattern, db=db)
        # Player caches: nba_api:players_active:*, nba_api:players_all_including_rookies:*
        total += _cache.clear_pattern("nba_api:players*:*", db=db)
        return total
    finally:
        db.close()

@router.post("/sync/players")
def sync_players():
    """Sync player data from NBA API"""
    try:
        players = NBADataService.fetch_all_players_including_rookies()
        return {"status": "success", "count": len(players)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/players/clean-recent-names")
def clean_recent_player_names(db: Session = Depends(get_db)):
    """Clean full_name, first_name, last_name for recent players only (those with team_id set — on a roster this year or last)."""
    try:
        recent = db.query(Player).filter(Player.team_id.isnot(None)).all()
        updated = 0
        for p in recent:
            if not p.full_name:
                continue
            cleaned = _clean_player_name(p.full_name)
            if cleaned == (p.full_name or ""):
                continue
            p.full_name = cleaned
            parts = cleaned.split()
            if len(parts) >= 2:
                p.first_name = parts[0]
                p.last_name = " ".join(parts[1:])
            elif len(parts) == 1:
                p.first_name = parts[0]
                p.last_name = ""
            updated += 1
        db.commit()
        return {"status": "success", "recent_players": len(recent), "names_updated": updated}
    except Exception as e:
        if db:
            db.rollback()
        return {"status": "error", "message": str(e)}


@router.post("/sync/teams")
def sync_teams():
    """Sync team data from NBA API"""
    try:
        teams = NBADataService.fetch_all_teams()
        return {"status": "success", "count": len(teams), "teams": teams}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/teams/status")
def teams_status():
    """Get team data status and verify player-team assignments"""
    try:
        teams = NBADataService.fetch_all_teams()
        players = NBADataService.fetch_all_players_including_rookies()
        
        # Check cache status - teams are cached with date-based key
        from datetime import datetime
        from ..services.cache_service import get_cache_service
        cache = get_cache_service()
        today_str = datetime.now().date().isoformat()
        cache_key = f"nba_api:teams:{today_str}"
        cached = cache.get(cache_key) is not None
        
        # Verify player-team assignments
        from ..services.team_player_service import TeamPlayerService
        
        # Count players with teams (using normalization to handle team_id=0)
        players_with_teams = [p for p in players if TeamPlayerService.normalize_team_id(p.get("team_id")) is not None]
        players_without_teams = [p for p in players if TeamPlayerService.normalize_team_id(p.get("team_id")) is None]
        
        # Count teams with players
        teams_with_players = {}
        teams_without_players = []
        
        for team in teams:
            team_id = team.get("id")
            team_players = TeamPlayerService.get_players_for_team(team_id)
            if team_players:
                teams_with_players[team_id] = {
                    "id": team_id,
                    "name": team.get("full_name"),
                    "abbreviation": team.get("abbreviation"),
                    "player_count": len(team_players)
                }
            else:
                teams_without_players.append({
                    "id": team_id,
                    "name": team.get("full_name"),
                    "abbreviation": team.get("abbreviation")
                })
        
        # Calculate integrity metrics
        total_players = len(players)
        total_teams = len(teams)
        teams_with_players_count = len(teams_with_players)
        players_with_teams_count = len(players_with_teams)
        
        # Determine overall status
        integrity_status = "good"
        if len(teams_without_players) > 5:  # More than 5 teams without players
            integrity_status = "warning"
        if len(players_without_teams) > total_players * 0.1:  # More than 10% players without teams
            integrity_status = "warning"
        if len(teams_without_players) > 10 or len(players_without_teams) > total_players * 0.2:
            integrity_status = "error"
        
        return {
            "status": "ready",
            "totalTeams": total_teams,
            "totalPlayers": total_players,
            "cached": cached,
            "lastUpdated": datetime.now().isoformat(),
            "integrity": {
                "status": integrity_status,
                "teamsWithPlayers": teams_with_players_count,
                "teamsWithoutPlayers": len(teams_without_players),
                "playersWithTeams": players_with_teams_count,
                "playersWithoutTeams": len(players_without_teams),
                "coverage": {
                    "teams": round((teams_with_players_count / total_teams * 100) if total_teams > 0 else 0, 1),
                    "players": round((players_with_teams_count / total_players * 100) if total_players > 0 else 0, 1)
                }
            },
            "teamsWithoutPlayers": teams_without_players[:10],  # First 10 for preview
            "teams": [
                {
                    "id": t.get("id"),
                    "full_name": t.get("full_name"),
                    "abbreviation": t.get("abbreviation"),
                    "conference": t.get("conference"),
                    "division": t.get("division"),
                }
                for t in teams[:10]  # Return first 10 for preview
            ]
        }
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to fetch teams status", error=str(e))
        return {"status": "error", "message": str(e)}

@router.post("/sync/stats")
def sync_stats():
    """Sync stats data"""
    return {"status": "queued", "message": "Stats sync queued for background processing"}

@router.post("/scan/best-bets")
def scan_best_bets(
    season: Optional[str] = Query(None, description="Season to analyze (defaults to current season)"),
    min_confidence: Optional[float] = Query(65.0, description="Minimum confidence threshold"),
    limit: Optional[int] = Query(50, description="Maximum number of suggestions")
):
    """Scan today's games and generate best prop bets"""
    try:
        results = PropScannerService.scan_best_bets_for_today(
            season=season or get_current_season(),
            min_confidence=min_confidence or 65.0,
            limit=limit or 50
        )
        scanned_at = datetime.now()
        _set_best_bets_cache(results, ttl=3600)
        return {
            "status": "success",
            "count": len(results),
            "scannedAt": scanned_at.isoformat(),
            "results": results[:20]  # Return first 20 for preview
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/best-bets")
def get_best_bets():
    """Get cached best bets from last scan"""
    cached = _get_best_bets_cache()
    if cached:
        return {
            "results": cached.get("results", []),
            "count": len(cached.get("results", [])),
            "lastScanned": cached.get("scanned_at")
        }
    return {
        "results": [],
        "count": 0,
        "lastScanned": None
    }

@router.get("/scan/status")
def scan_status():
    """Get scanning service status"""
    try:
        games = NBADataService.fetch_todays_games()
        players = NBADataService.fetch_all_players_including_rookies()
        cached = _get_best_bets_cache()
        best_bets_count = len(cached.get("results", [])) if cached else 0
        last_scan = cached.get("scanned_at") if cached else None
        return {
            "status": "ready",
            "todayGames": len(games),
            "totalPlayers": len(players),
            "lastScan": last_scan,
            "bestBetsCount": best_bets_count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/health")
def health():
    """System health check with data consistency info"""
    try:
        games = NBADataService.fetch_todays_games()
        players = NBADataService.fetch_all_players_including_rookies()
        
        # Check cache status
        today_str = date.today().isoformat()
        daily_props_cached = _get_daily_props_cache(today_str)
        high_hit_rate_cached = _get_high_hit_rate_cache(today_str)
        best_bets_cached = _get_best_bets_cache()
        
        return {
            "status": "healthy",
            "nbaApiAvailable": True,
            "todayGames": len(games),
            "totalPlayers": len(players),
            "dataConsistency": {
                "dailyProps": {
                    "cached": daily_props_cached is not None,
                    "valid": daily_props_cached is not None,
                    "lastUpdated": None,  # Cache service doesn't store separate timestamp
                    "count": len(daily_props_cached.get("items", [])) if daily_props_cached else 0
                },
                "highHitRate": {
                    "cached": high_hit_rate_cached is not None,
                    "valid": high_hit_rate_cached is not None,
                    "lastUpdated": None,
                    "count": len(high_hit_rate_cached.get("items", [])) if high_hit_rate_cached else 0
                },
                "bestBets": {
                    "cached": best_bets_cached is not None,
                    "lastUpdated": best_bets_cached.get("scanned_at") if best_bets_cached else None,
                    "count": len(best_bets_cached.get("results", [])) if best_bets_cached else 0
                }
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "nbaApiAvailable": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/refresh/daily-props")
@limiter.limit("5/hour")  # Rate limit: 5 requests per hour per IP (expensive operation)
def refresh_daily_props(
    request: Request,
    min_confidence: Optional[float] = Query(50.0, description="Minimum confidence threshold"),
    limit: Optional[int] = Query(50, description="Maximum number of results")
):
    """Manually refresh daily props cache"""
    try:
        result = DailyPropsService.get_top_props_for_date(
            date=None,  # Today
            season=None,  # Current season
            min_confidence=min_confidence,
            limit=limit
        )
        cached_at = datetime.now()
        _set_daily_props_cache(result, ttl=86400)
        return {
            "status": "success",
            "count": len(result.get("items", [])),
            "cachedAt": cached_at.isoformat(),
            "message": f"Cached {len(result.get('items', []))} daily props"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/refresh/high-hit-rate")
@limiter.limit("5/hour")  # Rate limit: 5 requests per hour per IP (expensive operation)
def refresh_high_hit_rate(
    request: Request,
    min_hit_rate: Optional[float] = Query(0.75, description="Minimum hit rate threshold"),
    limit: Optional[int] = Query(10, description="Maximum number of results"),
    last_n: Optional[int] = Query(10, description="Number of recent games to consider")
):
    """Manually refresh high hit rate bets cache"""
    try:
        result = HighHitRateService.get_high_hit_rate_bets(
            date=None,  # Today
            season=None,  # Current season
            min_hit_rate=min_hit_rate,
            limit=limit,
            last_n=last_n
        )
        cached_at = datetime.now()
        _set_high_hit_rate_cache(result, ttl=86400)
        return {
            "status": "success",
            "count": len(result.get("items", [])),
            "cachedAt": cached_at.isoformat(),
            "message": f"Cached {len(result.get('items', []))} high hit rate bets"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/refresh/top-picks")
@limiter.limit("5/hour")
def refresh_top_picks(
    request: Request,
    limit: int = Query(12, description="Max picks to cache"),
    min_confidence: float = Query(62.0, description="Minimum confidence (62+ = strong/lock only)"),
):
    """Regenerate the unified top-picks cache. Uses higher confidence by default for fewer, stronger picks."""
    try:
        result = BestPicksService.get_top_picks(limit=limit, min_confidence=min_confidence)
        target = result.get("date", date.today().isoformat())
        _cache.set(f"top_picks:{target}", result, ttl=86400)
        return {
            "status": "success",
            "count": len(result.get("items", [])),
            "cachedAt": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _compute_and_cache_stat_leaders(season: Optional[str] = None) -> dict:
    """Compute stat leaders from already-cached game logs and cache the result."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    season = season or get_current_season()
    today_str = datetime.now().date().isoformat()
    players = NBADataService.fetch_all_players_including_rookies()
    active = [p for p in players if p.get("team_id") and p.get("team_id") != 0]

    leaders: dict = {"PTS": [], "AST": [], "REB": [], "3PM": []}

    def _process(player):
        pid = player.get("id")
        if not pid:
            return None
        logs = NBADataService.fetch_player_game_log(pid, season)
        if not logs or len(logs) < 5:
            return None
        n = len(logs)
        pts = sum(float(g.get("pts", 0) or 0) for g in logs) / n
        ast = sum(float(g.get("ast", 0) or 0) for g in logs) / n
        reb = sum(float(g.get("reb", 0) or 0) for g in logs) / n
        tpm = sum(float(g.get("tpm", 0) or 0) for g in logs) / n
        name = player.get("full_name") or (player.get("first_name", "") + " " + player.get("last_name", "")).strip()
        return {"playerId": pid, "playerName": name or f"Player {pid}",
                "PTS": round(pts, 1), "AST": round(ast, 1),
                "REB": round(reb, 1), "3PM": round(tpm, 1)}

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(_process, p): p for p in active}
        for f in as_completed(futs):
            try:
                r = f.result(timeout=60)
                if r:
                    for cat in leaders:
                        leaders[cat].append({"playerId": r["playerId"],
                                             "playerName": r["playerName"],
                                             "value": r[cat]})
            except Exception:
                continue

    for cat in leaders:
        leaders[cat].sort(key=lambda x: x["value"], reverse=True)
        leaders[cat] = leaders[cat][:20]

    result = {"items": leaders}
    if any(leaders[cat] for cat in leaders):
        _cache.set(f"stat_leaders:{today_str}", result, ttl=86400)
    total = sum(len(leaders[c]) for c in leaders)
    return {"status": "success", "total_entries": total}


@router.post("/refresh/stat-leaders")
@limiter.limit("20/hour")
def refresh_stat_leaders(request: Request):
    """Pre-compute stat leaders from game logs and cache the result."""
    try:
        return _compute_and_cache_stat_leaders()
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/refresh/defensive-ranks")
@limiter.limit("5/hour")
def refresh_defensive_ranks(
    request: Request,
    season: Optional[str] = Query(None, description="Season (e.g. 2025-26). Defaults to current season.")
):
    """Pre-compute opponent defense ranks (PTS/REB/AST/3PM) for all teams and cache for 24h.
    Ensures Opponent Defense Rank cards on player profiles show values instead of —."""
    try:
        ranks = ContextCollector._calculate_defensive_ranks(season or get_current_season())
        teams_count = len(ranks) if ranks else 0
        return {
            "status": "success",
            "teamsRanked": teams_count,
            "message": f"Cached defensive ranks for {teams_count} teams (24h)"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/players/missing-from-espn")
def players_missing_from_espn():
    """
    Compare ESPN current rosters to app player list. Returns names that appear on
    ESPN rosters but are not in the app (e.g. rookies not yet in nba_api static data).
    Add them to backend/app/data/rookie_merge.json with nba_id and team_abbr (from nba.com).
    """
    try:
        espn_name_to_team, _ = NBADataService._fetch_espn_roster_mapping()
        all_players = NBADataService.fetch_all_players_including_rookies() or []
        app_names_lower = {(p.get("full_name") or "").strip().lower() for p in all_players if (p.get("full_name") or "").strip()}
        # NBA team_id -> abbreviation (first abbr wins for duplicates)
        id_to_abbr = {}
        for abbr, tid in NBADataService.ESPN_ABBR_TO_NBA_ID.items():
            if tid not in id_to_abbr:
                id_to_abbr[tid] = abbr
        missing = []
        for name_lower, team_id in espn_name_to_team.items():
            if name_lower and name_lower not in app_names_lower:
                abbr = id_to_abbr.get(team_id, "")
                missing.append({"name": name_lower.title(), "team_abbr": abbr, "team_id": team_id})
        missing.sort(key=lambda x: (x["team_abbr"], x["name"]))
        return {"missing": missing, "count": len(missing)}
    except Exception as e:
        return {"missing": [], "count": 0, "error": str(e)}


@router.post("/refresh/offensive-ranks")
@limiter.limit("5/hour")
def refresh_offensive_ranks(
    request: Request,
    season: Optional[str] = Query(None, description="Season (e.g. 2025-26). Defaults to current season.")
):
    """Pre-compute team offense ranks (PTS/REB/AST/3PM) for all teams and cache for 24h."""
    try:
        ranks = ContextCollector._calculate_offensive_ranks(season or get_current_season())
        teams_count = len(ranks) if ranks else 0
        return {
            "status": "success",
            "teamsRanked": teams_count,
            "message": f"Cached offensive ranks for {teams_count} teams (24h)"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/refresh/pace-ranks")
@limiter.limit("5/hour")
def refresh_pace_ranks(
    request: Request,
    season: Optional[str] = Query(None, description="Season (e.g. 2025-26). Defaults to current season.")
):
    """Pre-compute team pace (possessions per game) ranks for all teams and cache for 24h."""
    try:
        ranks = ContextCollector._calculate_pace_ranks(season or get_current_season())
        return {
            "status": "success",
            "teamsRanked": len(ranks),
            "message": f"Cached pace ranks for {len(ranks)} teams (24h)"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/refresh/position-defense-ranks")
@limiter.limit("5/hour")
def refresh_position_defense_ranks(
    request: Request,
    season: Optional[str] = Query(None, description="Season (e.g. 2025-26). Defaults to current season.")
):
    """Pre-compute position-based defensive ranks (PG/SG/SF/PF/C) for all teams and cache for 24h."""
    try:
        ranks = ContextCollector._calculate_position_defensive_ranks(season or get_current_season())
        return {
            "status": "success",
            "positions": list(ranks.keys()),
            "message": f"Cached position defense ranks for {len(ranks)} positions (24h)"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/refresh/all")
@limiter.limit("10/hour")
def refresh_all(request: Request):
    """Refresh all cached data
    
    WARNING: This endpoint makes many external API calls and should be used sparingly.
    It regenerates both daily props and high hit rate caches, which can involve
    fetching game logs for dozens of players.
    """
    results = {}
    
    # Refresh daily props
    try:
        daily_result = DailyPropsService.get_top_props_for_date(
            date=None,
            season=None,
            min_confidence=50.0,
            limit=50
        )
        _set_daily_props_cache(daily_result, ttl=86400)
        results["dailyProps"] = {
            "status": "success",
            "count": len(daily_result.get("items", []))
        }
    except Exception as e:
        results["dailyProps"] = {"status": "error", "message": str(e)}
    
    # Refresh high hit rate
    try:
        hit_rate_result = HighHitRateService.get_high_hit_rate_bets(
            date=None,
            season=None,
            min_hit_rate=0.75,
            limit=10,
            last_n=10
        )
        _set_high_hit_rate_cache(hit_rate_result, ttl=86400)
        results["highHitRate"] = {
            "status": "success",
            "count": len(hit_rate_result.get("items", []))
        }
    except Exception as e:
        results["highHitRate"] = {"status": "error", "message": str(e)}
    
    # Refresh best bets
    try:
        best_bets_result = PropScannerService.scan_best_bets_for_today(
            season=get_current_season(),
            min_confidence=65.0,
            limit=50
        )
        _set_best_bets_cache(best_bets_result, ttl=3600)
        results["bestBets"] = {
            "status": "success",
            "count": len(best_bets_result)
        }
    except Exception as e:
        results["bestBets"] = {"status": "error", "message": str(e)}

    # Refresh unified top picks
    try:
        top_picks_result = BestPicksService.get_top_picks(limit=12, min_confidence=62.0)
        target = top_picks_result.get("date", date.today().isoformat())
        _cache.set(f"top_picks:{target}", top_picks_result, ttl=86400)
        results["topPicks"] = {
            "status": "success",
            "count": len(top_picks_result.get("items", []))
        }
    except Exception as e:
        results["topPicks"] = {"status": "error", "message": str(e)}

    # Refresh stat leaders (uses game logs cached above)
    try:
        results["statLeaders"] = _compute_and_cache_stat_leaders()
    except Exception as e:
        results["statLeaders"] = {"status": "error", "message": str(e)}

    # Pre-warm opponent defense and offense ranks
    try:
        ranks = ContextCollector._calculate_defensive_ranks(get_current_season())
        results["defensiveRanks"] = {
            "status": "success",
            "teamsRanked": len(ranks) if ranks else 0
        }
    except Exception as e:
        results["defensiveRanks"] = {"status": "error", "message": str(e)}
    try:
        off_ranks = ContextCollector._calculate_offensive_ranks(get_current_season())
        results["offensiveRanks"] = {
            "status": "success",
            "teamsRanked": len(off_ranks) if off_ranks else 0
        }
    except Exception as e:
        results["offensiveRanks"] = {"status": "error", "message": str(e)}

    # Game predictions (Today's Games Predictions section)
    try:
        pred_svc = get_game_prediction_service()
        preds = pred_svc.get_todays_predictions(date.today())
        results["gamePredictions"] = {"status": "success", "count": len(preds)}
    except Exception as e:
        results["gamePredictions"] = {"status": "error", "message": str(e)}

    return {
        "status": "success",
        "results": results,
        "refreshedAt": datetime.now().isoformat()
    }


@router.post("/warm-dashboard")
@limiter.limit("10/hour")
def warm_dashboard(request: Request):
    """Warm all caches used by the homepage: Top Picks, AI Pick of the Day, Players to Watch, Hot form, Hot players.
    Safe to call from 6am cron after refresh jobs; fills any missing caches so dashboard sections load."""
    today_str = date.today().isoformat()
    results = {}
    # Daily props (base for pick-of-the-day and filtering)
    if not _get_daily_props_cache(today_str):
        try:
            r = DailyPropsService.get_top_props_for_date(date=today_str, season=get_current_season(), min_confidence=50.0, limit=100)
            _set_daily_props_cache(r, target_date=today_str, ttl=86400)
            results["dailyProps"] = len(r.get("items", []))
        except Exception as e:
            results["dailyProps"] = str(e)
    else:
        results["dailyProps"] = "cached"
    # Top picks
    if not _cache.get(f"top_picks:{today_str}"):
        try:
            r = BestPicksService.get_top_picks(date=today_str, limit=12, min_confidence=62.0)
            _cache.set(f"top_picks:{today_str}", r, ttl=86400)
            results["topPicks"] = len(r.get("items", []))
        except Exception as e:
            results["topPicks"] = str(e)
    else:
        results["topPicks"] = "cached"
    # Pick of the day (derive from daily props)
    if not _cache.get(f"pick_of_the_day:{today_str}"):
        try:
            items = (_get_daily_props_cache(today_str) or {}).get("items", [])
            items = [i for i in items if (i.get("gameDate") or i.get("game_date") or "").startswith(today_str[:10])]
            if items:
                items.sort(key=lambda x: (x.get("confidence") or 0), reverse=True)
                pick = {
                    "playerId": items[0].get("playerId"),
                    "playerName": items[0].get("playerName"),
                    "type": items[0].get("type"),
                    "marketLine": items[0].get("marketLine") or items[0].get("fairLine"),
                    "fairLine": items[0].get("fairLine"),
                    "suggestion": items[0].get("suggestion", "over"),
                    "confidence": items[0].get("confidence"),
                    "rationale": items[0].get("rationale"),
                    "gameDate": items[0].get("gameDate") or items[0].get("game_date"),
                    "confidenceSource": items[0].get("confidenceSource"),
                    "rationaleSource": items[0].get("rationaleSource"),
                    "mlAvailable": items[0].get("mlAvailable"),
                    "matchup_score": items[0].get("matchup_score"),
                    "insight_type": items[0].get("insight_type"),
                    "matchup_explanation": items[0].get("matchup_explanation"),
                    "opponent_abbr": items[0].get("opponent_abbr"),
                    "opponent_def_rank_vs_position": items[0].get("opponent_def_rank_vs_position"),
                    "supporting_metrics": items[0].get("supporting_metrics"),
                }
                _cache.set(f"pick_of_the_day:{today_str}", pick, ttl=86400)
                try:
                    from ..services.accuracy_tracking_service import record_pick_of_the_day

                    record_pick_of_the_day(date.fromisoformat(today_str), pick)
                except Exception:
                    pass
                results["pickOfTheDay"] = 1
            else:
                results["pickOfTheDay"] = 0
        except Exception as e:
            results["pickOfTheDay"] = str(e)
    else:
        results["pickOfTheDay"] = "cached"
    # Hot form (high confidence, hot form only)
    if not _cache.get(f"hot_form:{today_str}"):
        try:
            r = DailyPropsService.get_top_props_for_date(
                date=today_str, season=get_current_season(), min_confidence=70.0, limit=50, hot_form_only=True
            )
            items = r.get("items", [])
            if items:
                _cache.set(f"hot_form:{today_str}", {"items": items, "date": today_str}, ttl=86400)
            results["hotForm"] = len(items)
        except Exception as e:
            results["hotForm"] = str(e)
    else:
        results["hotForm"] = "cached"
    # Stat leaders (Players to Watch)
    try:
        _compute_and_cache_stat_leaders()
        results["statLeaders"] = "ok"
    except Exception as e:
        results["statLeaders"] = str(e)
    # Game predictions (Today's Games Predictions section)
    try:
        pred_svc = get_game_prediction_service()
        preds = pred_svc.get_todays_predictions(date.today())
        results["gamePredictions"] = len(preds)
    except Exception as e:
        results["gamePredictions"] = str(e)
    # Best Match of the Day (LLM or fallback)
    if not _cache.get(f"best_match_of_the_day:{today_str}"):
        try:
            from ..routers.games_v1 import compute_best_match_of_the_day
            best_match = compute_best_match_of_the_day(date.today())
            if best_match is not None:
                _cache.set(f"best_match_of_the_day:{today_str}", best_match, ttl=86400)
            results["bestMatchOfTheDay"] = 1 if best_match else 0
        except Exception as e:
            results["bestMatchOfTheDay"] = str(e)
    else:
        results["bestMatchOfTheDay"] = "cached"
    return {"status": "success", "date": today_str, "results": results}


@router.post("/cache/clear")
def clear_cache():
    """Clear all dashboard, team, and defensive/rank caches. Next request will repopulate; use Warm dashboard to prefill."""
    count = _clear_cache()
    return {
        "status": "success",
        "message": "All caches cleared. Refresh the page or click Warm dashboard to reload data.",
        "entries_cleared": count,
        "clearedAt": datetime.now().isoformat()
    }

@router.post("/cache/clear/daily-props")
def clear_daily_props_cache():
    """Clear daily props cache only"""
    db = next(get_db())
    try:
        _cache.clear_pattern("daily_props:*", db=db)
        return {"status": "success", "message": "Daily props cache cleared"}
    finally:
        db.close()

@router.post("/cache/clear/high-hit-rate")
def clear_high_hit_rate_cache():
    """Clear high hit rate cache only"""
    db = next(get_db())
    try:
        _cache.clear_pattern("high_hit_rate:*", db=db)
        return {"status": "success", "message": "High hit rate cache cleared"}
    finally:
        db.close()

@router.post("/cache/clear/best-bets")
def clear_best_bets_cache():
    """Clear best bets cache only"""
    db = next(get_db())
    try:
        _cache.delete("best_bets:latest", db=db)
        return {"status": "success", "message": "Best bets cache cleared"}
    finally:
        db.close()

@router.post("/cache/clear/todays-games")
def clear_todays_games_cache():
    """Clear today's games and top-picks cache so they refetch (e.g. after NBA API was empty and ESPN fallback is now used)."""
    db = next(get_db())
    try:
        n = _cache.clear_pattern("nba_api:todays_games:*", db=db)
        m = _cache.clear_pattern("top_picks:*", db=db)
        return {
            "status": "success",
            "message": "Today's games and top-picks cache cleared; next request will refetch.",
            "todays_games_cleared": n,
            "top_picks_cleared": m
        }
    finally:
        db.close()


@router.post("/cache/clear/game-predictions")
def clear_game_predictions_cache():
    """Clear game predictions list and detail caches. Next request to /games/predictions will rebuild from live ESPN scoreboard, def/off ranks, and team stats."""
    db = next(get_db())
    try:
        n = _cache.clear_pattern("game_predictions%", db=db)
        m = _cache.clear_pattern("game_prediction_detail%", db=db)
        return {
            "status": "success",
            "message": "Game predictions cache cleared; next request will rebuild with current data.",
            "game_predictions_cleared": n,
            "game_prediction_detail_cleared": m
        }
    finally:
        db.close()


@router.post("/ml/train")
def ml_train(db: Session = Depends(get_db)):
    """Trigger ML model training on historical bets and AI feature sets. Requires sufficient settled UserBet + AIFeatureSet data."""
    try:
        from ..services.ml_models.trainer import ModelTrainer
        trainer = ModelTrainer(use_xgboost=True)
        result = trainer.train_models(db, min_samples=50)
        return {"status": "success" if result.get("success") else "error", "result": result}
    except ImportError as e:
        return {"status": "error", "message": f"ML dependencies missing: {e}"}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@router.post("/ml/retrain")
def ml_retrain(min_samples: int = Query(50, ge=10, le=500)):
    """Full retrain pipeline: train models and update ml_model_version in AppSettings. For weekly cron or manual run."""
    try:
        from ..services.ml_models.retrain_pipeline import run_retrain
        result = run_retrain(min_samples=min_samples)
        return {"status": "success" if result.get("success") else "error", "result": result}
    except ImportError as e:
        return {"status": "error", "message": f"ML dependencies missing: {e}"}
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@router.post("/settle-accuracy")
def settle_accuracy(
    settle_date: Optional[str] = Query(None, description="Date to settle YYYY-MM-DD (default: yesterday)"),
    season: Optional[str] = Query(None, description="Season for player game logs when settling (defaults to current season)"),
):
    """Settle game predictions, AI pick-of-the-day, and Top Picks (prop) accuracy for a date (e.g. after games complete)."""
    from ..services.accuracy_tracking_service import settle_all_for_date
    target = date.fromisoformat(settle_date) if settle_date else (date.today() - timedelta(days=1))
    try:
        result = settle_all_for_date(target, season=season or get_current_season())
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/cache/clear/teams")
def clear_teams_cache():
    """Clear teams and players cache"""
    db = next(get_db())
    try:
        # Clear teams cache (pattern: nba_api:teams:*)
        teams_count = _cache.clear_pattern("nba_api:teams:*", db=db)
        # Clear players cache (pattern: nba_api:players*:*)
        players_count = _cache.clear_pattern("nba_api:players*:*", db=db)
        return {
            "status": "success",
            "message": "Teams and players cache cleared",
            "teams_cleared": teams_count,
            "players_cleared": players_count
        }
    finally:
        db.close()

@router.post("/cache/cleanup")
def cleanup_expired_cache(db: Session = Depends(get_db)):
    """Clean up expired cache entries"""
    try:
        count = _cache.cleanup_expired(db=db)
        return {
            "status": "success",
            "message": f"Cleaned up {count} expired cache entries",
            "count": count
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _today_str_eastern() -> str:
    """Today's date in Eastern (NBA primary timezone), for cache keys that use ET."""
    try:
        import pytz
        et_tz = pytz.timezone("America/New_York")
        return datetime.now(et_tz).date().isoformat()
    except Exception:
        return date.today().isoformat()


@router.get("/cache/status")
def cache_status():
    """Get cache status for all services including Redis status"""
    try:
        today_str = date.today().isoformat()
        today_et_str = _today_str_eastern()
        daily_props_cached = _get_daily_props_cache(today_str)
        high_hit_rate_cached = _get_high_hit_rate_cache(today_str)
        best_bets_cached = _get_best_bets_cache()
        
        # Get cache service stats including Redis status
        cache_stats = _cache.get_stats()
        
        # NBA API cache keys use Eastern date for todays_games
        nba_todays_games = _cache.get(f"nba_api:todays_games:{today_et_str}") is not None
        if not nba_todays_games:
            nba_todays_games = _cache.get(f"nba_api:todays_games:{today_str}") is not None
        
        return {
            "cacheBackend": {
                "type": cache_stats.get("backend", "unknown"),
                "redisAvailable": cache_stats.get("redis_available", False),
                "redisKeys": cache_stats.get("redis_keys", 0) if cache_stats.get("redis_available") else None,
                "sqliteEntries": cache_stats.get("total_entries", 0),
                "expiredEntries": cache_stats.get("expired_entries", 0)
            },
            "dailyProps": {
                "cached": daily_props_cached is not None,
                "valid": daily_props_cached is not None,
                "date": today_str if daily_props_cached else None,
                "lastUpdated": None,  # Cache service handles TTL internally
                "count": len(daily_props_cached.get("items", [])) if daily_props_cached else 0
            },
            "highHitRate": {
                "cached": high_hit_rate_cached is not None,
                "valid": high_hit_rate_cached is not None,
                "date": today_str if high_hit_rate_cached else None,
                "lastUpdated": None,
                "count": len(high_hit_rate_cached.get("items", [])) if high_hit_rate_cached else 0
            },
            "bestBets": {
                "cached": best_bets_cached is not None,
                "lastUpdated": best_bets_cached.get("scanned_at") if best_bets_cached else None,
                "count": len(best_bets_cached.get("results", [])) if best_bets_cached else 0
            },
            "nbaApiCache": {
                "teams": _cache.get(f"nba_api:teams:{today_str}") is not None,
                "players": _cache.get(f"nba_api:players_all_including_rookies:{today_str}") is not None,
                "todaysGames": nba_todays_games
            }
        }
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Failed to get cache status", error=str(e))
        return {
            "error": str(e),
            "cacheBackend": {"type": "unknown", "redisAvailable": False},
            "dailyProps": {"cached": False, "valid": False, "count": 0},
            "highHitRate": {"cached": False, "valid": False, "count": 0},
            "bestBets": {"cached": False, "count": 0},
            "nbaApiCache": {"teams": False, "players": False, "todaysGames": False}
        }

@router.get("/cache/redis/test")
def test_redis_connection():
    """Test Redis connection and return detailed status"""
    import os
    from ..services.cache_service import get_cache_service
    
    cache = get_cache_service()
    redis_url = os.getenv("REDIS_URL")
    
    result = {
        "redisUrlConfigured": redis_url is not None and redis_url != "",
        "redisUrl": redis_url if redis_url else None,
        "cacheBackend": "unknown",
        "redisAvailable": False,
        "redisConnected": False,
        "redisKeys": None,
        "testKey": None,
        "testValue": None,
        "error": None
    }
    
    try:
        cache_stats = cache.get_stats()
        result["cacheBackend"] = cache_stats.get("backend", "unknown")
        result["redisAvailable"] = cache_stats.get("redis_available", False)
        
        if result["redisAvailable"]:
            result["redisConnected"] = True
            result["redisKeys"] = cache_stats.get("redis_keys", 0)
            
            # Test write/read
            test_key = "redis_test_connection"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            cache.set(test_key, test_value, ttl=60)
            retrieved = cache.get(test_key)
            
            if retrieved and retrieved.get("test"):
                result["testKey"] = test_key
                result["testValue"] = retrieved
                # Clean up
                cache.delete(test_key)
            else:
                result["error"] = "Redis write/read test failed"
        else:
            result["error"] = "Redis is not available. Check REDIS_URL environment variable."
            
    except Exception as e:
        result["error"] = str(e)
        result["redisConnected"] = False
    
    return result

@router.get("/settings/ai-enabled")
def get_ai_enabled(db: Session = Depends(get_db)):
    """Get AI enabled status"""
    try:
        enabled = SettingsService.get_ai_enabled(db)
        return {
            "aiEnabled": enabled,
            "status": "enabled" if enabled else "disabled"
        }
    except Exception as e:
        return {"aiEnabled": False, "status": "error", "error": str(e)}

class AIEnabledRequest(BaseModel):
    enabled: bool

@router.post("/settings/ai-enabled")
def set_ai_enabled(request: AIEnabledRequest, db: Session = Depends(get_db)):
    """Enable or disable AI features"""
    try:
        SettingsService.set_ai_enabled(request.enabled, db)
        return {
            "status": "success",
            "aiEnabled": request.enabled,
            "message": f"AI features {'enabled' if request.enabled else 'disabled'}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@router.get("/settings")
def get_all_settings(db: Session = Depends(get_db)):
    """Get all application settings"""
    try:
        settings = SettingsService.get_all_settings(db)
        return {"settings": settings}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Data Integrity & Checksum Endpoints
_last_integrity_check: Optional[Dict] = None
_last_integrity_check_time: Optional[datetime] = None

@router.post("/data-integrity/check")
def run_data_integrity_check(
    season: Optional[str] = Query(None, description="Season to check"),
    db: Session = Depends(get_db)
):
    """Run full data integrity check comparing source data with database"""
    global _last_integrity_check, _last_integrity_check_time
    try:
        results = DataIntegrityService.run_full_integrity_check(db, season)
        _last_integrity_check = results
        _last_integrity_check_time = datetime.now()
        return {
            "status": "success",
            "results": results,
            "checked_at": _last_integrity_check_time.isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/data-integrity/status")
def get_data_integrity_status():
    """Get last data integrity check results"""
    global _last_integrity_check, _last_integrity_check_time
    if not _last_integrity_check:
        return {
            "status": "no_check",
            "message": "No integrity check has been run yet"
        }
    return {
        "status": "success",
        "results": _last_integrity_check,
        "checked_at": _last_integrity_check_time.isoformat() if _last_integrity_check_time else None
    }

@router.post("/data-integrity/check/players")
def check_players_integrity(db: Session = Depends(get_db)):
    """Check only players data integrity"""
    try:
        results = DataIntegrityService.check_players_integrity(db)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/data-integrity/check/game-stats")
def check_game_stats_integrity(
    season: Optional[str] = Query(None),
    player_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Check only game stats data integrity"""
    try:
        results = DataIntegrityService.check_game_stats_integrity(db, season, player_id)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/data-integrity/check/prop-suggestions")
def check_prop_suggestions_integrity(db: Session = Depends(get_db)):
    """Check only prop suggestions data integrity"""
    try:
        results = DataIntegrityService.check_prop_suggestions_integrity(db)
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/cache/refresh/player-logs")
def refresh_player_logs_cache(
    player_id: Optional[int] = Query(None, description="Player ID to refresh. If not provided, checks for finished games and invalidates all relevant caches.")
):
    """
    Manually refresh player game logs cache.
    If player_id is provided, invalidates cache for that specific player.
    If not provided, checks for finished games and invalidates caches for all players in finished games.
    """
    try:
        if player_id:
            # Invalidate cache for specific player
            invalidated = GameStatusMonitor.invalidate_cache_for_player(player_id)
            return {
                "status": "success",
                "message": f"Cache invalidated for player {player_id}",
                "player_id": player_id,
                "invalidated": invalidated
            }
        else:
            # Check for finished games and invalidate relevant caches
            result = GameStatusMonitor.check_and_invalidate_finished_games()
            return {
                "status": "success",
                "message": "Checked finished games and invalidated relevant caches",
                **result
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/rate-limits")
def get_rate_limits_status():
    """
    Get rate limit status for all external API providers.
    Shows current usage and limits for API-NBA and ESPN.
    
    Returns:
        Rate limit status for all providers
    """
    try:
        rate_limiter = get_rate_limiter()
        status = rate_limiter.get_all_providers_status()
        return {
            "status": "success",
            "providers": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/debug/player-game-log")
def debug_player_game_log(
    player_id: int = Query(..., description="Player ID to inspect"),
    season: Optional[str] = Query(None, description="Season string (e.g., '2025-26'). Defaults to current season.")
):
    """
    Debug endpoint to inspect raw API response for player game logs.
    Shows exactly what data is returned from the NBA API, including all columns and raw values.
    
    This is useful for debugging issues with minutes or other fields not being parsed correctly.
    
    Args:
        player_id: NBA player ID
        season: Optional season string
        
    Returns:
        Raw API response data with detailed column information
    """
    try:
        from nba_api.stats.endpoints import playergamelog
        import pandas as pd
        import structlog
        
        logger = structlog.get_logger()
        season_to_use = season or get_current_season()
        
        logger.info("Debug: Fetching player game log", player_id=player_id, season=season_to_use)
        
        # Fetch raw data from NBA API
        gl = playergamelog.PlayerGameLog(player_id=player_id, season=season_to_use)
        df = gl.get_data_frames()[0]
        
        # Convert DataFrame to dict for JSON serialization
        raw_data = []
        for idx, row in df.iterrows():
            row_dict = {}
            for col in df.columns:
                val = row.get(col)
                # Convert pandas types to native Python types
                if pd.isna(val):
                    row_dict[col] = None
                elif isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
                    row_dict[col] = str(val)
                else:
                    row_dict[col] = val
            raw_data.append(row_dict)
        
        # Check for minutes-related columns
        minutes_columns = [col for col in df.columns if any(x in col.upper() for x in ["MIN", "MP", "MINUTES"])]
        
        # Sample first row's minutes data
        sample_minutes_data = {}
        if len(df) > 0:
            first_row = df.iloc[0]
            for col in minutes_columns:
                sample_minutes_data[col] = {
                    "raw_value": str(first_row.get(col)),
                    "type": str(type(first_row.get(col))),
                    "is_null": pd.isna(first_row.get(col)) if col in first_row.index else True
                }
        
        # Parse minutes using the same logic as the service
        parsed_items = []
        for idx, row in df.iterrows():
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
                    if ":" in min_str:
                        parts = min_str.split(":")
                        if len(parts) >= 2:
                            minutes = float(parts[0]) + (float(parts[1]) / 60.0)
                        elif len(parts) == 1:
                            minutes = float(parts[0])
                    else:
                        minutes = float(min_str)
                except (ValueError, TypeError):
                    minutes = 0.0
            
            parsed_items.append({
                "game_id": str(row.get("Game_ID", "")),
                "game_date": str(row.get("GAME_DATE", "")),
                "raw_minutes_value": min_str,
                "minutes_column_found": min_col_found,
                "parsed_minutes": minutes
            })
        
        return {
            "status": "success",
            "player_id": player_id,
            "season": season_to_use,
            "summary": {
                "total_games": len(df),
                "available_columns": list(df.columns),
                "minutes_columns_found": minutes_columns,
                "sample_minutes_data": sample_minutes_data
            },
            "raw_data": raw_data[:10],  # First 10 games to avoid huge response
            "parsed_minutes_sample": parsed_items[:10],  # First 10 parsed results
            "all_parsed_minutes": [item["parsed_minutes"] for item in parsed_items],
            "minutes_statistics": {
                "total_games": len(parsed_items),
                "games_with_minutes": len([m for m in [item["parsed_minutes"] for item in parsed_items] if m > 0]),
                "games_without_minutes": len([m for m in [item["parsed_minutes"] for item in parsed_items] if m == 0]),
                "average_minutes": sum([item["parsed_minutes"] for item in parsed_items]) / len(parsed_items) if parsed_items else 0.0,
                "min_minutes": min([item["parsed_minutes"] for item in parsed_items]) if parsed_items else 0.0,
                "max_minutes": max([item["parsed_minutes"] for item in parsed_items]) if parsed_items else 0.0
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
