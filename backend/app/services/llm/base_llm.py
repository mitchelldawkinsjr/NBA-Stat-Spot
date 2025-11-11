"""
Base LLM Service - Abstract interface for LLM services
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


class BaseLLMService(ABC):
    """Abstract base class for LLM services"""
    
    @abstractmethod
    def generate_rationale(
        self,
        player_name: str,
        prop_type: str,
        line_value: float,
        direction: str,
        confidence: float,
        ml_confidence: Optional[float],
        stats: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        espn_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a human-readable rationale for a prop bet recommendation.
        
        Args:
            player_name: Player's name
            prop_type: Prop type (PTS, REB, AST, 3PM, PRA)
            line_value: Betting line value
            direction: "over" or "under"
            confidence: Confidence score (0-100)
            ml_confidence: ML confidence score if available
            stats: Dictionary with statistical data
            context: Optional context data (injuries, matchups, etc.)
            
        Returns:
            Human-readable rationale string
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        pass
    
    def generate_over_under_rationale(
        self,
        home_team: str,
        away_team: str,
        current_total: int,
        projected_total: float,
        live_line: Optional[float],
        recommendation: str,
        confidence: str,
        key_factors: list[str],
        game_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a human-readable rationale for an over/under recommendation.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            current_total: Current combined score
            projected_total: Projected final total
            live_line: Current betting line (optional)
            recommendation: "OVER", "UNDER", or "NO BET"
            confidence: Confidence level ("HIGH", "MEDIUM", "LOW")
            key_factors: List of key factors affecting the analysis
            game_context: Optional additional game context
            
        Returns:
            Human-readable rationale string
        """
        # Default implementation - can be overridden
        factors_text = ". ".join(key_factors) if key_factors else "No specific factors identified."
        rationale = f"{away_team} @ {home_team}: Current total is {current_total}. "
        rationale += f"Projected final total: {projected_total:.1f}. "
        if live_line:
            diff = projected_total - live_line
            rationale += f"Line: {live_line}. "
            if abs(diff) > 3:
                rationale += f"Projection is {abs(diff):.1f} points {'above' if diff > 0 else 'below'} the line. "
        rationale += f"Recommendation: {recommendation} ({confidence} confidence). "
        rationale += factors_text
        return rationale
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the LLM service.
        
        Returns:
            Dictionary with health status information
        """
        pass

