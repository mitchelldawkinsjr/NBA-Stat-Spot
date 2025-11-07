from __future__ import annotations
from typing import Any, Dict, List
from .nba_api_service import NBADataService

class DataSyncService:
    def sync_teams(self) -> List[Dict[str, Any]]:
        return NBADataService.fetch_all_teams()

    def sync_players(self) -> List[Dict[str, Any]]:
        return NBADataService.fetch_active_players()

    def sync_player_stats(self, player_id: int, lookback_days: int = 30) -> Dict[str, Any]:
        return {"player_id": player_id, "synced": True}

    def sync_featured_players(self) -> Dict[str, Any]:
        return {"status": "ok"}

    def sync_todays_lineups(self) -> Dict[str, Any]:
        return {"games": NBADataService.fetch_todays_games()}
