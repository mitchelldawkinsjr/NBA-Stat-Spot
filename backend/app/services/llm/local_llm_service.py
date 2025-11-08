"""
Local LLM Service - Uses local LLM (Ollama/LlamaCpp) for rationale generation
"""
from __future__ import annotations
from typing import Dict, Optional, Any
import os
from .base_llm import BaseLLMService

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False


class LocalLLMService(BaseLLMService):
    """Local LLM service using Ollama or LlamaCpp"""
    
    def __init__(self, provider: str = "ollama", model_name: str = "llama3.2", model_path: Optional[str] = None):
        """
        Initialize local LLM service.
        
        Args:
            provider: "ollama" or "llamacpp"
            model_name: Model name (for Ollama) or path (for LlamaCpp)
            model_path: Path to model file (for LlamaCpp)
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.model_path = model_path
        self._available = False
        self._model = None
        
        if self.provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ImportError("Ollama library not available. Install with: pip install ollama")
            self._available = True
        elif self.provider == "llamacpp":
            if not LLAMA_CPP_AVAILABLE:
                raise ImportError("llama-cpp-python not available")
            if not model_path:
                raise ValueError("model_path required for LlamaCpp")
            try:
                self._model = Llama(model_path=model_path, n_ctx=2048, verbose=False)
                self._available = True
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("Error loading LlamaCpp model", error=str(e))
                self._available = False
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
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
        Generate rationale using local LLM.
        
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
            raise RuntimeError("Local LLM service not available")
        
        # Build prompt
        prompt = self._build_prompt(
            player_name, prop_type, line_value, direction,
            confidence, ml_confidence, stats, context
        )
        
        try:
            if self.provider == "ollama":
                response = ollama.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        "temperature": 0.7,
                        "num_predict": 300
                    }
                )
                rationale = response["response"].strip()
            elif self.provider == "llamacpp":
                if not self._model:
                    raise RuntimeError("LlamaCpp model not loaded")
                response = self._model(
                    prompt,
                    max_tokens=300,
                    temperature=0.7,
                    stop=["\n\n", "Player:", "Prop:"]
                )
                rationale = response["choices"][0]["text"].strip()
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            
            return rationale
        except Exception as e:
            print(f"Error generating rationale with local LLM: {e}")
            raise
    
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
        """Build the prompt for rationale generation"""
        hit_rate = stats.get("hit_rate", 0)
        hit_rate_over = stats.get("hit_rate_over", 0)
        recent = stats.get("recent", {})
        trend = recent.get("trend", "flat")
        avg = recent.get("avg", 0)
        
        prompt = f"""Generate a concise rationale for this NBA prop bet:

Player: {player_name}
Bet: {prop_type} {direction.upper()} {line_value}
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
        
        prompt += "\n\nRationale:"
        
        return prompt
    
    def is_available(self) -> bool:
        """Check if local LLM service is available"""
        return self._available
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        if not self._available:
            return {
                "available": False,
                "provider": self.provider,
                "status": "unavailable"
            }
        
        try:
            if self.provider == "ollama":
                # Test with a simple prompt
                test_response = ollama.generate(
                    model=self.model_name,
                    prompt="test",
                    options={"num_predict": 5}
                )
                return {
                    "available": True,
                    "provider": self.provider,
                    "model": self.model_name,
                    "status": "healthy"
                }
            elif self.provider == "llamacpp":
                if not self._model:
                    return {
                        "available": False,
                        "provider": self.provider,
                        "status": "model_not_loaded"
                    }
                return {
                    "available": True,
                    "provider": self.provider,
                    "model": self.model_path,
                    "status": "healthy"
                }
        except Exception as e:
            return {
                "available": False,
                "provider": self.provider,
                "status": "unhealthy",
                "error": str(e)
            }
        
        return {
            "available": False,
            "provider": self.provider,
            "status": "unknown"
        }

