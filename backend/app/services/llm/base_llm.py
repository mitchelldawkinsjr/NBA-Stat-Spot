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
        context: Optional[Dict[str, Any]] = None
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
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the LLM service.
        
        Returns:
            Dictionary with health status information
        """
        pass

