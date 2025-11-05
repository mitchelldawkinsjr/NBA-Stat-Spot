from __future__ import annotations
from typing import List, Dict

class PropFilter:
    @staticmethod
    def filter_by_confidence(suggestions: List[Dict], min_confidence: float = 65.0) -> List[Dict]:
        return [s for s in suggestions if (s.get("confidence") or 0) >= min_confidence]

    @staticmethod
    def rank_suggestions(suggestions: List[Dict], sort_by: str = "confidence") -> List[Dict]:
        return sorted(suggestions, key=lambda s: (s.get(sort_by) or 0), reverse=True)
