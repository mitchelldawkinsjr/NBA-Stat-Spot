"""
Data Integrity Service - Validates source data cleanliness and database consistency
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import json

from ..models.players import Player
from ..models.player_game_stats import PlayerGameStat
from ..models.prop_suggestions import PropSuggestion
from ..models.teams import Team
from ..services.nba_api_service import NBADataService


class DataIntegrityService:
    @staticmethod
    def calculate_checksum(data: Any) -> str:
        """Calculate MD5 checksum for data"""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    @staticmethod
    def check_players_integrity(db: Session) -> Dict[str, Any]:
        """Check player data integrity between NBA API and database"""
        issues = []
        stats = {
            "source_count": 0,
            "db_count": 0,
            "missing_in_db": 0,
            "missing_in_source": 0,
            "mismatches": 0,
            "checksum_source": None,
            "checksum_db": None,
        }
        
        try:
            # Fetch from source (NBA API)
            source_players = NBADataService.fetch_all_players_including_rookies()
            stats["source_count"] = len(source_players)
            
            # Create source checksum
            source_data = sorted([{"id": p.get("id"), "name": p.get("full_name"), "team_id": p.get("team_id")} for p in source_players], key=lambda x: x.get("id", 0))
            stats["checksum_source"] = DataIntegrityService.calculate_checksum(source_data)
            
            # Fetch from database
            db_players = db.query(Player).all()
            stats["db_count"] = len(db_players)
            
            # Create DB checksum
            db_data = sorted([{"id": p.id, "name": p.full_name, "team_id": p.team_id} for p in db_players], key=lambda x: x.get("id", 0))
            stats["checksum_db"] = DataIntegrityService.calculate_checksum(db_data)
            
            # Find missing players
            source_ids = {p.get("id") for p in source_players if p.get("id")}
            db_ids = {p.id for p in db_players}
            
            missing_in_db = source_ids - db_ids
            missing_in_source = db_ids - source_ids
            
            stats["missing_in_db"] = len(missing_in_db)
            stats["missing_in_source"] = len(missing_in_source)
            
            if missing_in_db:
                issues.append({
                    "type": "missing_in_db",
                    "severity": "high",
                    "message": f"{len(missing_in_db)} players in source but not in database",
                    "details": list(missing_in_db)[:10]  # First 10 IDs
                })
            
            if missing_in_source:
                issues.append({
                    "type": "missing_in_source",
                    "severity": "medium",
                    "message": f"{len(missing_in_source)} players in database but not in source (may be inactive/retired)",
                    "details": list(missing_in_source)[:10]
                })
            
            # Check for data mismatches (players that exist in both but have different data)
            source_map = {p.get("id"): p for p in source_players if p.get("id")}
            mismatches = []
            for db_player in db_players:
                if db_player.id in source_map:
                    source_player = source_map[db_player.id]
                    if source_player.get("full_name") != db_player.full_name:
                        mismatches.append({
                            "player_id": db_player.id,
                            "field": "full_name",
                            "source": source_player.get("full_name"),
                            "db": db_player.full_name
                        })
                    if source_player.get("team_id") != db_player.team_id:
                        mismatches.append({
                            "player_id": db_player.id,
                            "field": "team_id",
                            "source": source_player.get("team_id"),
                            "db": db_player.team_id
                        })
            
            stats["mismatches"] = len(mismatches)
            if mismatches:
                issues.append({
                    "type": "data_mismatch",
                    "severity": "high",
                    "message": f"{len(mismatches)} players have data mismatches",
                    "details": mismatches[:5]  # First 5 mismatches
                })
            
        except Exception as e:
            issues.append({
                "type": "error",
                "severity": "critical",
                "message": f"Error checking players integrity: {str(e)}",
                "details": None
            })
        
        return {
            "status": "pass" if not issues else "fail",
            "stats": stats,
            "issues": issues,
            "checked_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def check_game_stats_integrity(db: Session, season: Optional[str] = None, player_id: Optional[int] = None) -> Dict[str, Any]:
        """Check game stats integrity - verify stats in DB match source data"""
        issues = []
        stats = {
            "db_count": 0,
            "source_count": 0,
            "missing_in_db": 0,
            "stale_data": 0,
            "invalid_data": 0,
        }
        
        try:
            # Get sample of players to check
            if player_id:
                players_to_check = [player_id]
            else:
                # Check top 20 active players
                source_players = NBADataService.fetch_all_players_including_rookies()
                players_to_check = [p.get("id") for p in source_players[:20] if p.get("id") and p.get("team_id")]
            
            season_to_use = season or "2025-26"
            
            for pid in players_to_check:
                try:
                    # Fetch from source
                    source_logs = NBADataService.fetch_player_game_log(pid, season_to_use)
                    if not source_logs:
                        continue
                    
                    stats["source_count"] += len(source_logs)
                    
                    # Fetch from DB
                    db_stats = db.query(PlayerGameStat).filter(
                        PlayerGameStat.player_id == pid
                    ).all()
                    stats["db_count"] += len(db_stats)
                    
                    # Check for missing games in DB
                    source_game_ids = {log.get("game_id") for log in source_logs if log.get("game_id")}
                    db_game_ids = {stat.game_id for stat in db_stats if stat.game_id}
                    missing = source_game_ids - db_game_ids
                    
                    if missing:
                        stats["missing_in_db"] += len(missing)
                        issues.append({
                            "type": "missing_game_stats",
                            "severity": "medium",
                            "message": f"Player {pid}: {len(missing)} games missing in database",
                            "player_id": pid,
                            "missing_count": len(missing)
                        })
                    
                    # Check for invalid/null data
                    invalid_count = 0
                    for stat in db_stats:
                        if stat.points is None or stat.rebounds is None or stat.assists is None:
                            invalid_count += 1
                    
                    if invalid_count > 0:
                        stats["invalid_data"] += invalid_count
                        issues.append({
                            "type": "invalid_data",
                            "severity": "medium",
                            "message": f"Player {pid}: {invalid_count} stats with null values",
                            "player_id": pid
                        })
                
                except Exception as e:
                    issues.append({
                        "type": "error",
                        "severity": "low",
                        "message": f"Error checking player {pid}: {str(e)}",
                        "player_id": pid
                    })
                    continue
            
        except Exception as e:
            issues.append({
                "type": "error",
                "severity": "critical",
                "message": f"Error checking game stats integrity: {str(e)}",
                "details": None
            })
        
        return {
            "status": "pass" if not issues else "fail",
            "stats": stats,
            "issues": issues,
            "checked_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def check_prop_suggestions_integrity(db: Session) -> Dict[str, Any]:
        """Check prop suggestions data integrity"""
        issues = []
        stats = {
            "total_suggestions": 0,
            "recent_suggestions": 0,
            "stale_suggestions": 0,
            "invalid_confidence": 0,
            "missing_player": 0,
        }
        
        try:
            # Get all prop suggestions
            all_suggestions = db.query(PropSuggestion).all()
            stats["total_suggestions"] = len(all_suggestions)
            
            # Check for recent suggestions (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent = db.query(PropSuggestion).filter(
                PropSuggestion.created_at >= seven_days_ago
            ).count()
            stats["recent_suggestions"] = recent
            
            # Check for stale suggestions (older than 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            stale = db.query(PropSuggestion).filter(
                PropSuggestion.created_at < thirty_days_ago
            ).count()
            stats["stale_suggestions"] = stale
            
            # Check for invalid confidence scores
            invalid_confidence = db.query(PropSuggestion).filter(
                (PropSuggestion.confidence_score < 0) | (PropSuggestion.confidence_score > 100)
            ).count()
            stats["invalid_confidence"] = invalid_confidence
            
            if invalid_confidence > 0:
                issues.append({
                    "type": "invalid_confidence",
                    "severity": "high",
                    "message": f"{invalid_confidence} suggestions with invalid confidence scores (not 0-100)",
                })
            
            # Check for suggestions with missing players
            missing_player = db.query(PropSuggestion).outerjoin(Player).filter(
                Player.id.is_(None)
            ).count()
            stats["missing_player"] = missing_player
            
            if missing_player > 0:
                issues.append({
                    "type": "missing_player",
                    "severity": "high",
                    "message": f"{missing_player} suggestions reference non-existent players",
                })
            
            if stale > 100:
                issues.append({
                    "type": "stale_data",
                    "severity": "low",
                    "message": f"{stale} stale suggestions (older than 30 days) - consider cleanup",
                })
        
        except Exception as e:
            issues.append({
                "type": "error",
                "severity": "critical",
                "message": f"Error checking prop suggestions integrity: {str(e)}",
            })
        
        return {
            "status": "pass" if not issues else "fail",
            "stats": stats,
            "issues": issues,
            "checked_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def run_full_integrity_check(db: Session, season: Optional[str] = None) -> Dict[str, Any]:
        """Run complete data integrity check"""
        results = {
            "overall_status": "pass",
            "checks": {},
            "summary": {
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
            },
            "checked_at": datetime.now().isoformat()
        }
        
        # Check players
        players_check = DataIntegrityService.check_players_integrity(db)
        results["checks"]["players"] = players_check
        
        # Check game stats
        game_stats_check = DataIntegrityService.check_game_stats_integrity(db, season)
        results["checks"]["game_stats"] = game_stats_check
        
        # Check prop suggestions
        prop_suggestions_check = DataIntegrityService.check_prop_suggestions_integrity(db)
        results["checks"]["prop_suggestions"] = prop_suggestions_check
        
        # Aggregate issues
        all_issues = []
        for check_name, check_result in results["checks"].items():
            all_issues.extend(check_result.get("issues", []))
        
        # Count by severity
        for issue in all_issues:
            severity = issue.get("severity", "low")
            results["summary"]["total_issues"] += 1
            if severity == "critical":
                results["summary"]["critical_issues"] += 1
            elif severity == "high":
                results["summary"]["high_issues"] += 1
            elif severity == "medium":
                results["summary"]["medium_issues"] += 1
            else:
                results["summary"]["low_issues"] += 1
        
        # Determine overall status
        if results["summary"]["critical_issues"] > 0 or results["summary"]["high_issues"] > 5:
            results["overall_status"] = "fail"
        elif results["summary"]["high_issues"] > 0 or results["summary"]["medium_issues"] > 10:
            results["overall_status"] = "warning"
        
        results["all_issues"] = all_issues
        
        return results

