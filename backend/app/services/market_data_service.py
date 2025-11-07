"""
Market Data Service - Fetches and tracks betting market data
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.market_context import MarketContext
# PropBetEngine imported lazily to avoid circular import


class MarketDataService:
    """Fetches and manages betting market data including lines, odds, and public betting"""
    
    @staticmethod
    def fetch_market_line(
        player_id: int,
        prop_type: str,
        game_date: date,
        source: str = "internal"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch market line for a player prop from external sources.
        
        Args:
            player_id: Player ID
            prop_type: Prop type (PTS, REB, AST, 3PM, PRA)
            game_date: Date of the game
            source: Data source identifier
            
        Returns:
            Dictionary with market data, or None if unavailable
        """
        # Placeholder - in production, you'd integrate with sportsbook APIs or scraping
        # For now, return None to indicate no external market data
        # The system will use internal fair line calculations as fallback
        return None
    
    @staticmethod
    def calculate_fair_line(
        player_id: int,
        prop_type: str,
        season: Optional[str] = None
    ) -> Optional[float]:
        """
        Calculate fair line based on player's historical performance.
        
        Args:
            player_id: Player ID
            prop_type: Prop type (PTS, REB, AST, 3PM, PRA)
            season: Season string
            
        Returns:
            Fair line value, or None if unable to calculate
        """
        try:
            from ..services.nba_api_service import NBADataService
            
            logs = NBADataService.fetch_player_game_log(player_id, season)
            if not logs:
                return None
            
            # Map prop type to stat key
            stat_map = {
                "PTS": "pts",
                "REB": "reb",
                "AST": "ast",
                "3PM": "tpm",
                "PRA": "pra"  # Would need to calculate PRA from logs
            }
            
            stat_key = stat_map.get(prop_type)
            if not stat_key:
                return None
            
            # Lazy import to avoid circular dependency
            from ..services.prop_engine import PropBetEngine
            # Use PropBetEngine to determine fair line
            fair_line = PropBetEngine.determine_line_value(logs, stat_key)
            return fair_line
        except Exception:
            return None
    
    @staticmethod
    def get_or_create_market_context(
        player_id: int,
        prop_type: str,
        game_date: date,
        market_line: Optional[float] = None,
        opening_line: Optional[float] = None,
        over_odds: Optional[str] = None,
        under_odds: Optional[str] = None,
        db: Optional[Session] = None
    ) -> MarketContext:
        """
        Get or create market context for a player prop.
        
        Args:
            player_id: Player ID
            prop_type: Prop type
            game_date: Date of the game
            market_line: Current market line
            opening_line: Opening line
            over_odds: Over odds (American format)
            under_odds: Under odds (American format)
            db: Database session
            
        Returns:
            MarketContext object
        """
        # Calculate fair line if not provided
        if market_line is None:
            # Try to fetch from external source first
            market_data = MarketDataService.fetch_market_line(player_id, prop_type, game_date)
            if market_data:
                market_line = market_data.get("line")
                opening_line = market_data.get("opening_line", opening_line)
                over_odds = market_data.get("over_odds", over_odds)
                under_odds = market_data.get("under_odds", under_odds)
            else:
                # Fallback to calculated fair line
                from datetime import datetime
                season = f"{datetime.now().year}-{str(datetime.now().year + 1)[-2:]}"
                market_line = MarketDataService.calculate_fair_line(player_id, prop_type, season)
        
        # Calculate line movement
        line_movement = None
        if opening_line is not None and market_line is not None:
            line_movement = market_line - opening_line
        
        # Calculate line value (difference from fair line)
        line_value = None
        if market_line is not None:
            from datetime import datetime
            season = f"{datetime.now().year}-{str(datetime.now().year + 1)[-2:]}"
            fair_line = MarketDataService.calculate_fair_line(player_id, prop_type, season)
            if fair_line is not None:
                line_value = market_line - fair_line
        
        context = MarketContext(
            player_id=player_id,
            game_date=game_date,
            prop_type=prop_type,
            market_line=market_line or 0.0,
            opening_line=opening_line,
            line_movement=line_movement,
            over_odds=over_odds,
            under_odds=under_odds,
            fair_line=MarketDataService.calculate_fair_line(player_id, prop_type),
            line_value=line_value
        )
        
        if db:
            # Check if context already exists
            existing = db.query(MarketContext).filter(
                MarketContext.player_id == player_id,
                MarketContext.game_date == game_date,
                MarketContext.prop_type == prop_type
            ).first()
            
            if existing:
                # Update existing context
                for key, value in context.__dict__.items():
                    if not key.startswith('_') and key != 'id' and key != 'created_at':
                        setattr(existing, key, value)
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Create new context
                db.add(context)
                db.commit()
                db.refresh(context)
                return context
        
        return context

