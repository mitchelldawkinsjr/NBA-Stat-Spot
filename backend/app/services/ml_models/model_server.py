"""
Model Server - Manages ML model loading, caching, and health checks
"""
from __future__ import annotations
from typing import Dict, Optional, Any
from datetime import datetime
from .confidence_predictor import ConfidencePredictor
from .line_predictor import LinePredictor


class ModelServer:
    """Manages ML models with loading, caching, and health checks"""
    
    def __init__(self):
        """Initialize the model server"""
        self.confidence_predictor = ConfidencePredictor()
        self.line_predictor = LinePredictor()
        self.confidence_loaded = False
        self.line_loaded = False
        self.last_health_check = None
        self.health_status = {}
    
    def load_models(self) -> Dict[str, bool]:
        """
        Load all ML models.
        
        Returns:
            Dictionary with load status for each model
        """
        results = {}
        
        # Load confidence predictor
        try:
            self.confidence_loaded = self.confidence_predictor.load_model()
            results["confidence"] = self.confidence_loaded
        except Exception as e:
            print(f"Error loading confidence predictor: {e}")
            results["confidence"] = False
            self.confidence_loaded = False
        
        # Load line predictor
        try:
            self.line_loaded = self.line_predictor.load_model()
            results["line"] = self.line_loaded
        except Exception as e:
            print(f"Error loading line predictor: {e}")
            results["line"] = False
            self.line_loaded = False
        
        return results
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all models.
        
        Returns:
            Dictionary with health status for each model
        """
        self.last_health_check = datetime.now()
        
        health = {
            "confidence_model": {
                "loaded": self.confidence_loaded,
                "available": self.confidence_loaded and self.confidence_predictor.model is not None,
                "path": self.confidence_predictor.model_path
            },
            "line_model": {
                "loaded": self.line_loaded,
                "available": self.line_loaded and self.line_predictor.model is not None,
                "path": self.line_predictor.model_path
            },
            "last_check": self.last_health_check.isoformat()
        }
        
        self.health_status = health
        return health
    
    def predict_confidence(self, features: Dict[str, Any]) -> Optional[float]:
        """
        Predict confidence using the ML model.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Confidence score (0-100), or None if unavailable
        """
        if not self.confidence_loaded:
            self.load_models()
        
        if not self.confidence_loaded:
            return None
        
        return self.confidence_predictor.predict(features)
    
    def predict_line(self, features: Dict[str, Any]) -> Optional[float]:
        """
        Predict optimal line using the ML model.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Predicted line value, or None if unavailable
        """
        if not self.line_loaded:
            self.load_models()
        
        if not self.line_loaded:
            return None
        
        return self.line_predictor.predict(features)
    
    def is_available(self) -> bool:
        """
        Check if any models are available.
        
        Returns:
            True if at least one model is loaded
        """
        return self.confidence_loaded or self.line_loaded


# Global model server instance
_model_server: Optional[ModelServer] = None


def get_model_server() -> ModelServer:
    """
    Get or create the global model server instance.
    
    Returns:
        ModelServer instance
    """
    global _model_server
    if _model_server is None:
        _model_server = ModelServer()
        _model_server.load_models()
    return _model_server

