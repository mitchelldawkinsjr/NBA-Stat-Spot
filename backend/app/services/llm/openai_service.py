"""
OpenAI LLM Service - Uses OpenAI API for rationale generation
"""
from __future__ import annotations
from typing import Dict, Optional, Any
import os
from .base_llm import BaseLLMService

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI library not available. Install with: pip install openai")


class OpenAIService(BaseLLMService):
    """OpenAI LLM service for generating prop bet rationales"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library not available")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self._available = True
    
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
        Generate rationale using OpenAI API.
        
        Args:
            player_name: Player's name
            prop_type: Prop type
            line_value: Betting line
            direction: "over" or "under"
            confidence: Confidence score
            ml_confidence: ML confidence if available
            stats: Statistical data
            context: Optional context data
            
        Returns:
            Generated rationale string
        """
        if not self._available:
            raise RuntimeError("OpenAI service not available")
        
        # Build prompt
        prompt = self._build_prompt(
            player_name, prop_type, line_value, direction,
            confidence, ml_confidence, stats, context
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            rationale = response.choices[0].message.content.strip()
            return rationale
        except Exception as e:
            print(f"Error generating rationale with OpenAI: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for rationale generation"""
        return """You are an expert NBA betting analyst. Generate concise, data-driven rationales for prop bet recommendations.
        
Your rationales should:
- Be 2-3 sentences maximum
- Highlight key statistical factors
- Mention recent form trends
- Reference matchup context if relevant
- Be professional and objective
- Avoid gambling encouragement language"""
    
    def _build_prompt(
        self,
        player_name: str,
        prop_type: str,
        line_value: float,
        direction: str,
        confidence: float,
        ml_confidence: Optional[float],
        stats: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the user prompt for rationale generation"""
        hit_rate = stats.get("hit_rate", 0)
        hit_rate_over = stats.get("hit_rate_over", 0)
        recent = stats.get("recent", {})
        trend = recent.get("trend", "flat")
        avg = recent.get("avg", 0)
        
        prompt = f"""Generate a rationale for this prop bet recommendation:

Player: {player_name}
Prop: {prop_type} {direction.upper()} {line_value}
Confidence: {confidence}%"""
        
        if ml_confidence:
            prompt += f"\nML Confidence: {ml_confidence}%"
        
        prompt += f"""
Stats:
- Hit rate ({direction}): {hit_rate:.1%}
- Recent form: {trend} (avg: {avg:.1f})
- Season hit rate (over): {hit_rate_over:.1%}"""
        
        if context:
            if context.get("rest_days") is not None:
                prompt += f"\n- Rest days: {context['rest_days']}"
            if context.get("is_home_game"):
                prompt += "\n- Home game"
            if context.get("opponent_def_rank"):
                prompt += f"\n- Opponent defensive rank: {context['opponent_def_rank']}"
            if context.get("h2h_avg"):
                prompt += f"\n- H2H average: {context['h2h_avg']:.1f}"
        
        prompt += "\n\nGenerate a concise rationale explaining why this bet has the given confidence level."
        
        return prompt
    
    def is_available(self) -> bool:
        """Check if OpenAI service is available"""
        return self._available and self.api_key is not None
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            # Simple test call
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return {
                "available": True,
                "model": self.model,
                "status": "healthy"
            }
        except Exception as e:
            return {
                "available": False,
                "model": self.model,
                "status": "unhealthy",
                "error": str(e)
            }

