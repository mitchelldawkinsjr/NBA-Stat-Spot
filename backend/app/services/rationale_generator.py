"""
Rationale Generator Service - Generates human-readable explanations for prop bets
"""
from __future__ import annotations
from typing import Dict, Optional, Any
from .llm.base_llm import BaseLLMService
from .llm.openai_service import OpenAIService
from .llm.local_llm_service import LocalLLMService


class RationaleGenerator:
    """Generates rationales using LLM services with fallback chain"""
    
    def __init__(self):
        """Initialize rationale generator with fallback chain"""
        self.services: list[BaseLLMService] = []
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize LLM services in priority order"""
        # Try OpenAI first (if API key available)
        try:
            openai_service = OpenAIService()
            if openai_service.is_available():
                self.services.append(openai_service)
                print("OpenAI LLM service initialized")
        except Exception as e:
            print(f"OpenAI service not available: {e}")
        
        # Try local Ollama as fallback
        try:
            ollama_service = LocalLLMService(provider="ollama", model_name="llama3.2")
            if ollama_service.is_available():
                self.services.append(ollama_service)
                print("Ollama LLM service initialized")
        except Exception as e:
            print(f"Ollama service not available: {e}")
        
        # Try LlamaCpp as last resort (if model path configured)
        # This would require model_path to be set in config
        # try:
        #     llamacpp_service = LocalLLMService(provider="llamacpp", model_path="path/to/model")
        #     if llamacpp_service.is_available():
        #         self.services.append(llamacpp_service)
        # except Exception:
        #     pass
    
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
        Generate rationale using available LLM service with fallback.
        
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
            Human-readable rationale string, or fallback rationale if LLM unavailable
        """
        # Try each service in order
        for service in self.services:
            try:
                if service.is_available():
                    rationale = service.generate_rationale(
                        player_name, prop_type, line_value, direction,
                        confidence, ml_confidence, stats, context
                    )
                    return rationale
            except Exception as e:
                print(f"Error generating rationale with {service.__class__.__name__}: {e}")
                continue
        
        # Fallback to rule-based rationale
        return self._generate_fallback_rationale(
            player_name, prop_type, line_value, direction, confidence, stats, context
        )
    
    def _generate_fallback_rationale(
        self,
        player_name: str,
        prop_type: str,
        line_value: float,
        direction: str,
        confidence: float,
        stats: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a simple rule-based rationale as fallback"""
        hit_rate = stats.get("hit_rate", 0)
        recent = stats.get("recent", {})
        trend = recent.get("trend", "flat")
        avg = recent.get("avg", 0)
        
        rationale_parts = []
        
        # Add trend information
        if trend == "up":
            rationale_parts.append(f"{player_name} is in good form")
        elif trend == "down":
            rationale_parts.append(f"{player_name} has been struggling recently")
        else:
            rationale_parts.append(f"{player_name} has been consistent")
        
        # Add hit rate information
        if hit_rate >= 0.7:
            rationale_parts.append(f"with a strong {hit_rate:.0%} hit rate {direction} {line_value}")
        elif hit_rate >= 0.5:
            rationale_parts.append(f"with a {hit_rate:.0%} hit rate {direction} {line_value}")
        else:
            rationale_parts.append(f"though hit rate is {hit_rate:.0%} {direction} {line_value}")
        
        # Add context if available
        if context:
            if context.get("rest_days") == 0:
                rationale_parts.append("on a back-to-back")
            elif context.get("rest_days") and context.get("rest_days") >= 2:
                rationale_parts.append("with good rest")
            
            if context.get("is_home_game"):
                rationale_parts.append("at home")
            else:
                rationale_parts.append("on the road")
        
        rationale = ", ".join(rationale_parts) + "."
        return rationale
    
    def is_available(self) -> bool:
        """Check if any LLM service is available"""
        return len(self.services) > 0
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all services"""
        health = {
            "services": [],
            "available": False
        }
        
        for service in self.services:
            service_health = service.health_check()
            health["services"].append({
                "type": service.__class__.__name__,
                "health": service_health
            })
            if service_health.get("available"):
                health["available"] = True
        
        return health


# Global rationale generator instance
_rationale_generator: Optional[RationaleGenerator] = None


def get_rationale_generator() -> RationaleGenerator:
    """
    Get or create the global rationale generator instance.
    
    Returns:
        RationaleGenerator instance
    """
    global _rationale_generator
    if _rationale_generator is None:
        _rationale_generator = RationaleGenerator()
    return _rationale_generator

