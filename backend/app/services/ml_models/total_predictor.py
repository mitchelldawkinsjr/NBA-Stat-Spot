"""
Total Predictor Model - ML model for predicting final game totals for over/under analysis
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import os
import joblib
from pathlib import Path


class TotalPredictor:
    """ML model for predicting final game totals for over/under betting"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the total predictor.
        
        Args:
            model_path: Path to saved model file. If None, uses default location.
        """
        self.model = None
        self.model_path = model_path or self._get_default_model_path()
        self.is_loaded = False
    
    def _get_default_model_path(self) -> str:
        """Get default path for model file"""
        base_dir = Path(__file__).parent.parent.parent
        models_dir = base_dir / "models" / "ml_models"
        models_dir.mkdir(parents=True, exist_ok=True)
        return str(models_dir / "total_predictor.pkl")
    
    def load_model(self) -> bool:
        """
        Load the trained model from disk.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.is_loaded = True
                return True
            else:
                # Model doesn't exist yet - will be created during training
                self.is_loaded = False
                return False
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Error loading total predictor model", error=str(e))
            self.is_loaded = False
            return False
    
    def save_model(self, model: Any) -> bool:
        """
        Save a trained model to disk.
        
        Args:
            model: Trained model object
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(model, self.model_path)
            self.model = model
            self.is_loaded = True
            return True
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Error saving total predictor model", error=str(e))
            return False
    
    def predict(self, features: Dict[str, float]) -> Optional[float]:
        """
        Predict final game total based on current game state.
        
        Args:
            features: Dictionary of normalized feature values
            
        Returns:
            Predicted final total, or None if prediction fails
        """
        if not self.is_loaded or self.model is None:
            if not self.load_model():
                return None
        
        try:
            # Convert features dict to array format
            feature_array = self._features_to_array(features)
            
            # Make prediction
            prediction = self.model.predict(feature_array)
            
            # Extract prediction value
            total = float(prediction[0]) if hasattr(prediction, '__iter__') else float(prediction)
            
            return total
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Error making total prediction", error=str(e))
            return None
    
    def _features_to_array(self, features: Dict[str, float]) -> List[List[float]]:
        """
        Convert features dictionary to array format for model input.
        
        Args:
            features: Dictionary of normalized feature values
            
        Returns:
            2D array of feature values
        """
        # Define feature order (this should match training)
        feature_order = [
            'current_total',
            'home_score',
            'away_score',
            'score_differential',
            'quarter',
            'time_elapsed',
            'time_remaining',
            'time_elapsed_pct',
            'current_pace',
            'expected_pace',
            'pace_differential',
            'pace_ratio',
            'home_ppg',
            'away_ppg',
            'combined_ppg',
            'home_pace',
            'away_pace',
            'combined_pace',
            'points_per_minute',
            'projected_at_current_pace',
            'home_rest_days',
            'away_rest_days',
            'is_back_to_back_home',
            'is_back_to_back_away',
            'is_playoff',
            'is_close_game',
            'is_blowout',
            'is_late_game',
            'is_very_late',
            'is_overtime',
        ]
        
        # Extract features in order, with defaults for missing values
        feature_values = []
        for feature in feature_order:
            value = features.get(feature, 0.0)
            feature_values.append(float(value))
        
        return [feature_values]

