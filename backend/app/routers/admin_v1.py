from fastapi import APIRouter, Query
from typing import Optional, List, Dict
from datetime import datetime, date
from ..services.prop_scanner import PropScannerService
from ..services.nba_api_service import NBADataService
from ..services.daily_props_service import DailyPropsService
from ..services.high_hit_rate_service import HighHitRateService

router = APIRouter(prefix="/api/v1/admin", tags=["admin_v1"])

# Cache stores with daily TTL
_best_bets_cache: List[Dict] = []
_last_scan_time: Optional[datetime] = None

_daily_props_cache: Optional[Dict] = None
_daily_props_cache_date: Optional[date] = None
_daily_props_cache_time: Optional[datetime] = None

_high_hit_rate_cache: Optional[Dict] = None
_high_hit_rate_cache_date: Optional[date] = None
_high_hit_rate_cache_time: Optional[datetime] = None

def _is_cache_valid(cache_date: Optional[date], cache_time: Optional[datetime]) -> bool:
    """Check if cache is still valid (same day)"""
    if not cache_date or not cache_time:
        return False
    today = date.today()
    return cache_date == today

def _clear_cache():
    """Clear all caches"""
    global _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    global _high_hit_rate_cache, _high_hit_rate_cache_date, _high_hit_rate_cache_time
    _daily_props_cache = None
    _daily_props_cache_date = None
    _daily_props_cache_time = None
    _high_hit_rate_cache = None
    _high_hit_rate_cache_date = None
    _high_hit_rate_cache_time = None

@router.post("/sync/players")
def sync_players():
    """Sync player data from NBA API"""
    try:
        players = NBADataService.fetch_all_players_including_rookies()
        return {"status": "success", "count": len(players)}
    except Exception as e:
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
    global _best_bets_cache, _last_scan_time
    try:
        results = PropScannerService.scan_best_bets_for_today(
            season=season or "2025-26",
            min_confidence=min_confidence or 65.0,
            limit=limit or 50
        )
        _best_bets_cache = results
        _last_scan_time = datetime.now()
        return {
            "status": "success",
            "count": len(results),
            "scannedAt": _last_scan_time.isoformat(),
            "results": results[:20]  # Return first 20 for preview
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/best-bets")
def get_best_bets():
    """Get cached best bets from last scan"""
    global _best_bets_cache, _last_scan_time
    return {
        "results": _best_bets_cache,
        "count": len(_best_bets_cache),
        "lastScanned": _last_scan_time.isoformat() if _last_scan_time else None
    }

@router.get("/scan/status")
def scan_status():
    """Get scanning service status"""
    global _last_scan_time
    try:
        games = NBADataService.fetch_todays_games()
        players = NBADataService.fetch_all_players_including_rookies()
        return {
            "status": "ready",
            "todayGames": len(games),
            "totalPlayers": len(players),
            "lastScan": _last_scan_time.isoformat() if _last_scan_time else None,
            "bestBetsCount": len(_best_bets_cache)
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
        daily_props_valid = _is_cache_valid(_daily_props_cache_date, _daily_props_cache_time)
        high_hit_rate_valid = _is_cache_valid(_high_hit_rate_cache_date, _high_hit_rate_cache_time)
        
        return {
            "status": "healthy",
            "nbaApiAvailable": True,
            "todayGames": len(games),
            "totalPlayers": len(players),
            "dataConsistency": {
                "dailyProps": {
                    "cached": _daily_props_cache is not None,
                    "valid": daily_props_valid,
                    "lastUpdated": _daily_props_cache_time.isoformat() if _daily_props_cache_time else None,
                    "count": len(_daily_props_cache.get("items", [])) if _daily_props_cache else 0
                },
                "highHitRate": {
                    "cached": _high_hit_rate_cache is not None,
                    "valid": high_hit_rate_valid,
                    "lastUpdated": _high_hit_rate_cache_time.isoformat() if _high_hit_rate_cache_time else None,
                    "count": len(_high_hit_rate_cache.get("items", [])) if _high_hit_rate_cache else 0
                },
                "bestBets": {
                    "cached": len(_best_bets_cache) > 0,
                    "lastUpdated": _last_scan_time.isoformat() if _last_scan_time else None,
                    "count": len(_best_bets_cache)
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
    global _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    try:
        result = DailyPropsService.get_top_props_for_date(
            date=None,  # Today
            season=None,  # Current season
            min_confidence=min_confidence,
            limit=limit
        )
        _daily_props_cache = result
        _daily_props_cache_date = date.today()
        _daily_props_cache_time = datetime.now()
        return {
            "status": "success",
            "count": len(result.get("items", [])),
            "cachedAt": _daily_props_cache_time.isoformat(),
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
    global _high_hit_rate_cache, _high_hit_rate_cache_date, _high_hit_rate_cache_time
    try:
        result = HighHitRateService.get_high_hit_rate_bets(
            date=None,  # Today
            season=None,  # Current season
            min_hit_rate=min_hit_rate,
            limit=limit,
            last_n=last_n
        )
        _high_hit_rate_cache = result
        _high_hit_rate_cache_date = date.today()
        _high_hit_rate_cache_time = datetime.now()
        return {
            "status": "success",
            "count": len(result.get("items", [])),
            "cachedAt": _high_hit_rate_cache_time.isoformat(),
            "message": f"Cached {len(result.get('items', []))} high hit rate bets"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/refresh/all")
def refresh_all():
    """Refresh all cached data"""
    global _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    global _high_hit_rate_cache, _high_hit_rate_cache_date, _high_hit_rate_cache_time
    
    results = {}
    
    # Refresh daily props
    try:
        daily_result = DailyPropsService.get_top_props_for_date(
            date=None,
            season=None,
            min_confidence=50.0,
            limit=50
        )
        _daily_props_cache = daily_result
        _daily_props_cache_date = date.today()
        _daily_props_cache_time = datetime.now()
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
        _high_hit_rate_cache = hit_rate_result
        _high_hit_rate_cache_date = date.today()
        _high_hit_rate_cache_time = datetime.now()
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
    global _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    global _high_hit_rate_cache, _high_hit_rate_cache_date, _high_hit_rate_cache_time
    global _best_bets_cache, _last_scan_time
    
    _clear_cache()
    _best_bets_cache = []
    _last_scan_time = None
    
    return {
        "status": "success",
        "message": "All caches cleared",
        "clearedAt": datetime.now().isoformat()
    }

@router.post("/cache/clear/daily-props")
def clear_daily_props_cache():
    """Clear daily props cache only"""
    global _daily_props_cache, _daily_props_cache_date, _daily_props_cache_time
    _daily_props_cache = None
    _daily_props_cache_date = None
    _daily_props_cache_time = None
    return {"status": "success", "message": "Daily props cache cleared"}

@router.post("/cache/clear/high-hit-rate")
def clear_high_hit_rate_cache():
    """Clear high hit rate cache only"""
    global _high_hit_rate_cache, _high_hit_rate_cache_date, _high_hit_rate_cache_time
    _high_hit_rate_cache = None
    _high_hit_rate_cache_date = None
    _high_hit_rate_cache_time = None
    return {"status": "success", "message": "High hit rate cache cleared"}

@router.post("/cache/clear/best-bets")
def clear_best_bets_cache():
    """Clear best bets cache only"""
    global _best_bets_cache, _last_scan_time
    _best_bets_cache = []
    _last_scan_time = None
    return {"status": "success", "message": "Best bets cache cleared"}

@router.get("/cache/status")
def cache_status():
    """Get cache status for all services"""
    return {
        "dailyProps": {
            "cached": _daily_props_cache is not None,
            "valid": _is_cache_valid(_daily_props_cache_date, _daily_props_cache_time),
            "date": _daily_props_cache_date.isoformat() if _daily_props_cache_date else None,
            "lastUpdated": _daily_props_cache_time.isoformat() if _daily_props_cache_time else None,
            "count": len(_daily_props_cache.get("items", [])) if _daily_props_cache else 0
        },
        "highHitRate": {
            "cached": _high_hit_rate_cache is not None,
            "valid": _is_cache_valid(_high_hit_rate_cache_date, _high_hit_rate_cache_time),
            "date": _high_hit_rate_cache_date.isoformat() if _high_hit_rate_cache_date else None,
            "lastUpdated": _high_hit_rate_cache_time.isoformat() if _high_hit_rate_cache_time else None,
            "count": len(_high_hit_rate_cache.get("items", [])) if _high_hit_rate_cache else 0
        },
        "bestBets": {
            "cached": len(_best_bets_cache) > 0,
            "lastUpdated": _last_scan_time.isoformat() if _last_scan_time else None,
            "count": len(_best_bets_cache)
        }
    }
