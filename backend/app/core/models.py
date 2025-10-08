from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Player(BaseModel):
    id: int
    name: str
    team: Optional[str] = None

class GameLog(BaseModel):
    date: str
    opponent: str
    home: bool
    minutes: float
    pts: float
    reb: float
    ast: float
    tpm: float

class PropSuggestion(BaseModel):
    type: str
    fairLine: float
    confidence: float
    marketLine: Optional[float] = None
    edge: Optional[float] = None
    rationale: List[str] = []
    features: Dict[str, Any] = {}
    distribution: Dict[str, float] = {}
