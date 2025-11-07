"""
Enhanced Prop Response Models - Structured response format for AI-enhanced prop evaluations
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class PropSuggestionResponse(BaseModel):
    """Enhanced prop suggestion response with AI features"""
    type: str  # PTS, REB, AST, 3PM, PRA
    marketLine: float
    fairLine: float
    direction: str  # "over" or "under"
    confidence: float  # 0-100
    suggestion: str  # "over" or "under"
    hitRate: float  # 0-1
    hitRateOver: float  # 0-1
    hitRateUnder: float  # 0-1
    rationale: List[str]  # Array of rationale strings
    
    # AI-enhanced fields (optional)
    mlConfidence: Optional[float] = None  # ML model confidence (0-100)
    mlPredictedLine: Optional[float] = None  # ML predicted optimal line
    confidenceSource: Optional[str] = None  # "ml_blended", "rule_based", "ml_only"
    rationaleSource: Optional[str] = None  # "llm", "rule_based"
    mlAvailable: Optional[bool] = False  # Whether ML was used
    factors: Optional[Dict[str, Any]] = None  # Structured key factors

