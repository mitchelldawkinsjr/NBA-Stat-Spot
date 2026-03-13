"""
OpenAI LLM Service - Uses OpenAI API for rationale generation
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import os
from .base_llm import BaseLLMService
from .prompt_builder import (
    PROP_SYSTEM_PROMPT,
    OVER_UNDER_SYSTEM_PROMPT,
    GAME_OUTLOOK_SYSTEM_PROMPT,
    GAME_SUMMARY_SYSTEM_PROMPT,
    build_prop_rationale_prompt,
    build_over_under_prompt,
)

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
        context: Optional[Dict[str, Any]] = None,
        espn_context: Optional[Dict[str, Any]] = None
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
            confidence, ml_confidence, stats, context, espn_context
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            import structlog
            structlog.get_logger().error("Error generating rationale with OpenAI", error=str(e))
            raise

    def generate_from_prompt(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        """Generate text from a single user prompt with a lightweight NBA analyst system prompt."""
        if not self._available:
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert NBA analyst. Be concise, factual, and data-driven. Use only the information provided. No preamble."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return None

    def _get_system_prompt(self) -> str:
        return PROP_SYSTEM_PROMPT

    def _build_prompt(
        self,
        player_name: str,
        prop_type: str,
        line_value: float,
        direction: str,
        confidence: float,
        ml_confidence: Optional[float],
        stats: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        espn_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        import os
        depth = (os.getenv("LLM_REASONING_DEPTH") or "summary").strip().lower()
        if depth not in ("summary", "full"):
            depth = "summary"
        return build_prop_rationale_prompt(
            player_name=player_name,
            prop_type=prop_type,
            line_value=line_value,
            direction=direction,
            confidence=confidence,
            ml_confidence=ml_confidence,
            stats=stats,
            context=context,
            espn_context=espn_context,
            for_chat_api=True,
            reasoning_depth=depth,
        )

    def generate_over_under_rationale(
        self,
        home_team: str,
        away_team: str,
        current_total: int,
        projected_total: float,
        live_line: Optional[float],
        recommendation: str,
        confidence: str,
        key_factors: List[str],
        game_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate over/under rationale using OpenAI API."""
        if not self._available:
            raise RuntimeError("OpenAI service not available")

        prompt = build_over_under_prompt(
            home_team=home_team,
            away_team=away_team,
            current_total=current_total,
            projected_total=projected_total,
            live_line=live_line,
            recommendation=recommendation,
            confidence=confidence,
            key_factors=key_factors,
            game_context=game_context,
            for_chat_api=True,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": OVER_UNDER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Error generating over/under rationale with OpenAI", error=str(e))
            return super().generate_over_under_rationale(
                home_team, away_team, current_total, projected_total,
                live_line, recommendation, confidence, key_factors, game_context
            )
    
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

