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
                import structlog
                logger = structlog.get_logger()
                logger.info("OpenAI LLM service initialized")
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("OpenAI service not available", error=str(e))
        
        # Try local Ollama as fallback
        try:
            ollama_service = LocalLLMService(provider="ollama", model_name="llama3.2")
            if ollama_service.is_available():
                self.services.append(ollama_service)
                import structlog
                logger = structlog.get_logger()
                logger.info("Ollama LLM service initialized")
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Ollama service not available", error=str(e))
        
        # LlamaCpp support can be added if needed by configuring model_path
        # Example:
        # try:
        #     llamacpp_service = LocalLLMService(provider="llamacpp", model_path=os.getenv("LLAMA_MODEL_PATH"))
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
        context: Optional[Dict[str, Any]] = None,
        espn_context: Optional[Dict[str, Any]] = None
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
                        confidence, ml_confidence, stats, context, espn_context
                    )
                    return rationale
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("Error generating rationale", service=service.__class__.__name__, error=str(e))
                continue
        
        # Fallback to rule-based rationale
        return self._generate_fallback_rationale(
            player_name, prop_type, line_value, direction, confidence, stats, context, espn_context
        )
    
    def _generate_fallback_rationale(
        self,
        player_name: str,
        prop_type: str,
        line_value: float,
        direction: str,
        confidence: float,
        stats: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        espn_context: Optional[Dict[str, Any]] = None
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
        
        # Add ESPN context if available
        if espn_context:
            injury_status = espn_context.get("injury_status")
            if injury_status:
                if injury_status == "out":
                    rationale_parts.append(f"⚠️ Player is OUT")
                elif injury_status == "doubtful":
                    rationale_parts.append(f"⚠️ Player is DOUBTFUL")
                elif injury_status == "questionable":
                    rationale_parts.append(f"⚠️ Player is QUESTIONABLE")
                elif injury_status == "probable":
                    rationale_parts.append(f"Player is PROBABLE")
            
            conference_rank = espn_context.get("conference_rank")
            if conference_rank and conference_rank <= 8:
                rationale_parts.append(f"Team is {conference_rank} in conference")
            
            news_sentiment = espn_context.get("news_sentiment")
            if news_sentiment and abs(news_sentiment) > 0.3:
                if news_sentiment > 0:
                    rationale_parts.append("positive recent news")
                else:
                    rationale_parts.append("negative recent news")
        
        rationale = ", ".join(rationale_parts) + "."
        return rationale
    
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
        Generate over/under rationale using available LLM service with fallback.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            current_total: Current combined score
            projected_total: Projected final total
            live_line: Current betting line (optional)
            recommendation: "OVER", "UNDER", or "NO BET"
            confidence: Confidence level ("HIGH", "MEDIUM", "LOW")
            key_factors: List of key factors
            game_context: Optional additional game context
            
        Returns:
            Human-readable rationale string
        """
        # Try each service in order
        for service in self.services:
            try:
                if service.is_available():
                    rationale = service.generate_over_under_rationale(
                        home_team, away_team, current_total, projected_total,
                        live_line, recommendation, confidence, key_factors, game_context
                    )
                    return rationale
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.warning("Error generating over/under rationale", service=service.__class__.__name__, error=str(e))
                continue
        
        # Fallback to base implementation (create dummy instance to call method)
        from .llm.base_llm import BaseLLMService
        # Create a temporary instance to access the default implementation
        class DummyLLM(BaseLLMService):
            def generate_rationale(self, *args, **kwargs):
                return ""
            def is_available(self):
                return True
            def health_check(self):
                return {}
        
        dummy = DummyLLM()
        return dummy.generate_over_under_rationale(
            home_team, away_team, current_total, projected_total,
            live_line, recommendation, confidence, key_factors, game_context
        )
    
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

