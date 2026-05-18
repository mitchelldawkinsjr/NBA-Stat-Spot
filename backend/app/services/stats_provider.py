"""Pluggable stats source for accuracy settlement."""
from __future__ import annotations
import os
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .nba_api_service import NBADataService


class StatsProvider(ABC):
    @abstractmethod
    def fetch_player_game_log(
        self, player_id: int, season: str
    ) -> List[Dict[str, Any]]:
        ...


class GameLogStatsProvider(StatsProvider):
    def fetch_player_game_log(self, player_id: int, season: str) -> List[Dict[str, Any]]:
        return NBADataService.fetch_player_game_log(player_id, season)


class DbStatsProvider(StatsProvider):
    def fetch_player_game_log(self, player_id: int, season: str) -> List[Dict[str, Any]]:
        from ..database import SessionLocal
        from ..pipeline.repositories import player_stats_repo

        db = SessionLocal()
        try:
            logs = player_stats_repo.get_player_logs_from_stats(db, player_id, season, limit=40)
            if logs:
                return logs
        finally:
            db.close()
        return NBADataService.fetch_player_game_log(player_id, season)


def get_settlement_stats_provider() -> StatsProvider:
    if (os.getenv("PIPELINE_SETTLE_USE_DB") or "").strip().lower() in ("1", "true", "yes"):
        return DbStatsProvider()
    return GameLogStatsProvider()
