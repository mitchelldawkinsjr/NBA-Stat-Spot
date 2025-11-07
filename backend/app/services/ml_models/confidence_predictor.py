"""
Confidence Predictor Model - ML model for predicting prop bet confidence
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any
import os
import pickle
import joblib
from pathlib import Path


class ConfidencePredictor:
    """ML model for predicting confidence that a prop bet will hit"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the confidence predictor.
        
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
        return str(models_dir / "confidence_predictor.pkl")
    
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
            print(f"Error loading confidence predictor model: {e}")
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
            print(f"Error saving confidence predictor model: {e}")
            return False
    
    def predict(self, features: Dict[str, Any]) -> Optional[float]:
        """
        Predict confidence score for a prop bet.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Confidence score (0-100), or None if prediction fails
        """
        if not self.is_loaded or self.model is None:
            if not self.load_model():
                return None
        
        try:
            # Convert features dict to array format expected by model
            # This is a placeholder - actual implementation depends on model type
            feature_array = self._features_to_array(features)
            
            # Make prediction
            prediction = self.model.predict(feature_array)
            
            # Ensure prediction is in 0-100 range
            confidence = float(prediction[0]) if hasattr(prediction, '__iter__') else float(prediction)
            confidence = max(0.0, min(100.0, confidence))
            
            return confidence
        except Exception as e:
            print(f"Error making confidence prediction: {e}")
            return None
    
    def predict_proba(self, features: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Predict probability distribution for over/under.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            Dictionary with 'over' and 'under' probabilities, or None if prediction fails
        """
        if not self.is_loaded or self.model is None:
            if not self.load_model():
                return None
        
        try:
            feature_array = self._features_to_array(features)
            
            # Check if model supports predict_proba
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(feature_array)
                return {
                    "over": float(proba[0][1]) if len(proba[0]) > 1 else float(proba[0][0]),
                    "under": float(proba[0][0]) if len(proba[0]) > 1 else 1.0 - float(proba[0][0])
                }
            else:
                # Fallback: use predict and convert to probability
                confidence = self.predict(features)
                if confidence is not None:
                    prob_over = confidence / 100.0
                    return {
                        "over": prob_over,
                        "under": 1.0 - prob_over
                    }
                return None
        except Exception as e:
            print(f"Error making probability prediction: {e}")
            return None
    
    def _features_to_array(self, features: Dict[str, Any]) -> List[List[float]]:
        """
        Convert features dictionary to array format for model input.
        
        Args:
            features: Dictionary of feature values
            
        Returns:
            2D array of feature values
        """
        # Define feature order (this should match training)
        feature_order = [
            "rolling_avg_10",
            "rolling_avg_5",
            "season_avg",
            "variance",
            "momentum",
            "rest_days",
            "is_injured",
            "is_home_game",
            "opponent_def_rank_pts",
            "h2h_avg_pts",
            "h2h_games_played",
            "team_win_rate",
            "opponent_win_rate",
            "market_line",
            "line_value",
            "hit_rate_over",
            "hit_rate_under",
            "trend"
        ]
        
        # Extract features in order, with defaults for missing values
        feature_values = []
        for feature in feature_order:
            value = features.get(feature, 0.0)
            
            # Handle different types
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
            elif isinstance(value, str):
                # Encode string features
                if feature == "trend":
                    trend_map = {"up": 1.0, "flat": 0.5, "down": 0.0}
                    value = trend_map.get(value.lower(), 0.5)
                else:
                    value = 0.0
            elif value is None:
                value = 0.0
            
            feature_values.append(float(value))
        
        return [feature_values]

