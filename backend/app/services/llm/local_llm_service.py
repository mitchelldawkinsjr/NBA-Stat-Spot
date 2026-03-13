"""
Local LLM Service - Uses local or remote LLM (Ollama/LlamaCpp) for rationale generation.
Supports Ollama on a VPS via OLLAMA_HOST (e.g. http://your-vps:11434).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import os
from .base_llm import BaseLLMService
from .prompt_builder import build_prop_rationale_prompt, build_over_under_prompt

try:
    import ollama
    from ollama import Client as OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    ollama = None
    OllamaClient = None
    OLLAMA_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

# Default timeout for Ollama requests (remote VPS may be slower)
OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "90"))


class LocalLLMService(BaseLLMService):
    """Local or remote LLM service using Ollama or LlamaCpp"""
    
    def __init__(
        self,
        provider: str = "ollama",
        model_name: str = "llama3.2",
        model_path: Optional[str] = None,
        ollama_host: Optional[str] = None,
    ):
        """
        Initialize local LLM service.
        
        Args:
            provider: "ollama" or "llamacpp"
            model_name: Model name (for Ollama) or path (for LlamaCpp)
            model_path: Path to model file (for LlamaCpp)
            ollama_host: Base URL for Ollama (e.g. http://vps-ip:11434). Uses OLLAMA_HOST env if None.
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.model_path = model_path
        self._available = False
        self._model = None
        self._ollama_client: Optional[Any] = None

        if self.provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ImportError("Ollama library not available. Install with: pip install ollama")
            host = ollama_host or os.getenv("OLLAMA_HOST") or os.getenv("LLM_OLLAMA_BASE_URL")
            if host:
                self._ollama_client = OllamaClient(host=host, timeout=OLLAMA_REQUEST_TIMEOUT)
            else:
                self._ollama_client = OllamaClient(timeout=OLLAMA_REQUEST_TIMEOUT)
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
        context: Optional[Dict[str, Any]] = None,
        espn_context: Optional[Dict[str, Any]] = None
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
            confidence, ml_confidence, stats, context, espn_context
        )
        
        try:
            if self.provider == "ollama":
                response = self._ollama_client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={"temperature": 0.5, "num_predict": 300},
                )
                rationale = response.response.strip() if hasattr(response, "response") else response.get("response", "").strip()
            elif self.provider == "llamacpp":
                if not self._model:
                    raise RuntimeError("LlamaCpp model not loaded")
                response = self._model(
                    prompt,
                    max_tokens=300,
                    temperature=0.5,
                    stop=["\n\n", "PROP:", "Game:"],
                )
                rationale = response["choices"][0]["text"].strip()
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
            return rationale
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.error("Error generating rationale with local LLM", error=str(e))
            raise

    def generate_from_prompt(self, prompt: str, max_tokens: int = 300) -> Optional[str]:
        """Generate text from a single user prompt (temperature 0.5 for consistency)."""
        if not self._available:
            return None
        try:
            if self.provider == "ollama":
                response = self._ollama_client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={"temperature": 0.5, "num_predict": max_tokens},
                )
                return (response.response if hasattr(response, "response") else response.get("response", "") or "").strip()
            if self.provider == "llamacpp" and self._model:
                out = self._model(prompt, max_tokens=max_tokens, temperature=0.5, stop=["\n\n"])
                return (out["choices"][0]["text"] or "").strip()
        except Exception:
            pass
        return None

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
        game_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate over/under rationale using the enhanced O/U prompt (persona embedded for Ollama)."""
        if not self._available:
            raise RuntimeError("Local LLM service not available")
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
            for_chat_api=False,
        )
        try:
            if self.provider == "ollama":
                response = self._ollama_client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={"temperature": 0.5, "num_predict": 200},
                )
                return (response.response if hasattr(response, "response") else response.get("response", "") or "").strip()
            if self.provider == "llamacpp" and self._model:
                out = self._model(prompt, max_tokens=200, temperature=0.5, stop=["\n\n", "GAME:"])
                return (out["choices"][0]["text"] or "").strip()
        except Exception as e:
            import structlog
            structlog.get_logger().warning("Ollama O/U rationale failed", error=str(e))
        return super().generate_over_under_rationale(
            home_team, away_team, current_total, projected_total,
            live_line, recommendation, confidence, key_factors, game_context,
        )

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
        espn_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the single-prompt for local/Ollama models (persona embedded inline)."""
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
            for_chat_api=False,
            reasoning_depth=depth,
        )
    
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
                test_response = self._ollama_client.generate(
                    model=self.model_name,
                    prompt="test",
                    options={"num_predict": 5}
                )
                return {
                    "available": True,
                    "provider": self.provider,
                    "model": self.model_name,
                    "status": "healthy",
                    "host": os.getenv("OLLAMA_HOST") or os.getenv("LLM_OLLAMA_BASE_URL") or "localhost",
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

