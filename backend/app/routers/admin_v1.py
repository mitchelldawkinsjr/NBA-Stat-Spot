from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.prop_scanner import PropScannerService
from ..services.nba_api_service import NBADataService
from ..services.daily_props_service import DailyPropsService
from ..services.high_hit_rate_service import HighHitRateService
from ..services.settings_service import SettingsService
from ..services.data_integrity_service import DataIntegrityService
from ..services.game_status_monitor import GameStatusMonitor
from ..services.cache_service import get_cache_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin_v1"])

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
    """Clear all caches"""
    db = next(get_db())
    try:
        _cache.clear_pattern("daily_props:*", db=db)
        _cache.clear_pattern("high_hit_rate:*", db=db)
        _cache.delete("best_bets:latest", db=db)
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
        from cachetools.keys import hashkey
        from datetime import datetime
        cache_key = hashkey("teams", datetime.now().date().isoformat())
        from ..services.nba_api_service import a_cache
        cached = cache_key in a_cache
        
        # Verify player-team assignments
        from ..services.team_player_service import TeamPlayerService
        
        # Count players with teams
        players_with_teams = [p for p in players if p.get("team_id") is not None]
        players_without_teams = [p for p in players if p.get("team_id") is None]
        
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
    season: Optional[str] = Query("2025-26", description="Season to analyze"),
    min_confidence: Optional[float] = Query(65.0, description="Minimum confidence threshold"),
    limit: Optional[int] = Query(50, description="Maximum number of suggestions")
):
    """Scan today's games and generate best prop bets"""
    try:
        results = PropScannerService.scan_best_bets_for_today(
            season=season or "2025-26",
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
def refresh_daily_props(
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
def refresh_high_hit_rate(
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

@router.post("/refresh/all")
def refresh_all():
    """Refresh all cached data"""
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
    
    return {
        "status": "success",
        "results": results,
        "refreshedAt": datetime.now().isoformat()
    }

@router.post("/cache/clear")
def clear_cache():
    """Clear all caches"""
    _clear_cache()
    return {
        "status": "success",
        "message": "All caches cleared",
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

@router.get("/cache/status")
def cache_status():
    """Get cache status for all services"""
    today_str = date.today().isoformat()
    daily_props_cached = _get_daily_props_cache(today_str)
    high_hit_rate_cached = _get_high_hit_rate_cache(today_str)
    best_bets_cached = _get_best_bets_cache()
    
    return {
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
        }
    }

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
