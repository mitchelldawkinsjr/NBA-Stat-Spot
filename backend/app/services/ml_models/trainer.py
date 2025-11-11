"""
Model Trainer - Trains ML models for confidence and line prediction
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.ai_features import AIFeatureSet
from ..models.user_bets import UserBet
from .confidence_predictor import ConfidencePredictor
from .line_predictor import LinePredictor

try:
    from xgboost import XGBRegressor, XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    import structlog
    logger = structlog.get_logger()
    logger.warning("XGBoost not available. Will use scikit-learn models.")

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    import structlog
    logger = structlog.get_logger()
    logger.warning("scikit-learn not available. Cannot train models.")


class ModelTrainer:
    """Trains and evaluates ML models for prop bet predictions"""
    
    def __init__(self, use_xgboost: bool = True):
        """
        Initialize the model trainer.
        
        Args:
            use_xgboost: Whether to use XGBoost (True) or scikit-learn (False)
        """
        self.use_xgboost = use_xgboost and XGBOOST_AVAILABLE
        if not self.use_xgboost and not SKLEARN_AVAILABLE:
            raise ImportError("Neither XGBoost nor scikit-learn is available")
    
    def prepare_training_data(
        self,
        db: Session,
        min_samples: int = 100
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare training data from historical bets and outcomes.
        
        Args:
            db: Database session
            min_samples: Minimum number of samples required for training
            
        Returns:
            Tuple of (features_df, confidence_targets, line_targets)
        """
        # Fetch historical bets with outcomes
        settled_bets = db.query(UserBet).filter(
            UserBet.result.in_(["won", "lost"])
        ).all()
        
        if len(settled_bets) < min_samples:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Insufficient training data", settled_bets=len(settled_bets), min_samples=min_samples)
            return None, None, None
        
        # Fetch corresponding feature sets
        features_list = []
        confidence_targets = []
        line_targets = []
        
        for bet in settled_bets:
            # Get feature set for this bet
            feature_set = db.query(AIFeatureSet).filter(
                AIFeatureSet.player_id == bet.player_id,
                AIFeatureSet.game_date == bet.game_date,
                AIFeatureSet.prop_type == bet.prop_type
            ).first()
            
            if not feature_set:
                continue
            
            # Extract features
            features = {
                "rolling_avg_10": feature_set.rolling_avg_10 or 0.0,
                "rolling_avg_5": feature_set.rolling_avg_5 or 0.0,
                "season_avg": feature_set.season_avg or 0.0,
                "variance": feature_set.variance or 0.0,
                "momentum": feature_set.momentum or 0.0,
                "rest_days": feature_set.rest_days or 0.0,
                "is_injured": 1.0 if feature_set.is_injured else 0.0,
                "is_home_game": 1.0 if feature_set.is_home_game else 0.0,
                "opponent_def_rank": feature_set.opponent_def_rank or 0.0,
                "h2h_avg": feature_set.h2h_avg or 0.0,
                "h2h_games_played": feature_set.h2h_games_played or 0.0,
                "team_win_rate": feature_set.team_win_rate or 0.0,
                "opponent_win_rate": feature_set.opponent_win_rate or 0.0,
                "market_line": feature_set.market_line or 0.0,
                "line_value": feature_set.line_value or 0.0,
                "hit_rate_over": feature_set.hit_rate_over or 0.0,
                "hit_rate_under": feature_set.hit_rate_under or 0.0,
                "trend": 1.0 if feature_set.trend == "up" else (0.5 if feature_set.trend == "flat" else 0.0)
            }
            
            features_list.append(features)
            
            # Create targets
            # Confidence target: 100 if won, 0 if lost (for over bets)
            if bet.direction == "over":
                confidence = 100.0 if bet.result == "won" else 0.0
            else:
                confidence = 100.0 if bet.result == "won" else 0.0
            
            confidence_targets.append(confidence)
            
            # Line target: actual stat value
            if bet.actual_value is not None:
                line_targets.append(bet.actual_value)
            else:
                line_targets.append(bet.line_value)  # Fallback to line value
        
        if len(features_list) < min_samples:
            import structlog
            logger = structlog.get_logger()
            logger.warning("Insufficient samples for training", found=len(features_list), required=min_samples)
            return None, None, None
        
        # Convert to DataFrame
        features_df = pd.DataFrame(features_list)
        confidence_targets = pd.Series(confidence_targets)
        line_targets = pd.Series(line_targets)
        
        return features_df, confidence_targets, line_targets
    
    def train_confidence_model(
        self,
        features_df: pd.DataFrame,
        targets: pd.Series,
        test_size: float = 0.2
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Train confidence prediction model.
        
        Args:
            features_df: Feature DataFrame
            targets: Target values (confidence scores)
            test_size: Proportion of data to use for testing
            
        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for training")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, targets, test_size=test_size, random_state=42
        )
        
        # Train model
        if self.use_xgboost:
            model = XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
        else:
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        metrics = {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }
        
        return model, metrics
    
    def train_line_model(
        self,
        features_df: pd.DataFrame,
        targets: pd.Series,
        test_size: float = 0.2
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Train line prediction model.
        
        Args:
            features_df: Feature DataFrame
            targets: Target values (line values)
            test_size: Proportion of data to use for testing
            
        Returns:
            Tuple of (trained_model, metrics_dict)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for training")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features_df, targets, test_size=test_size, random_state=42
        )
        
        # Train model
        if self.use_xgboost:
            model = XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
        else:
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
        
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        
        metrics = {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "train_samples": len(X_train),
            "test_samples": len(X_test)
        }
        
        return model, metrics
    
    def train_models(self, db: Session, min_samples: int = 100) -> Dict[str, Any]:
        """
        Train both confidence and line prediction models.
        
        Args:
            db: Database session
            min_samples: Minimum number of samples required
            
        Returns:
            Dictionary with training results and metrics
        """
        import structlog
        logger = structlog.get_logger()
        logger.info("Preparing training data...")
        features_df, confidence_targets, line_targets = self.prepare_training_data(db, min_samples)
        
        if features_df is None:
            return {
                "success": False,
                "error": "Insufficient training data"
            }
        
        logger.info("Training on samples", count=len(features_df))
        
        # Train confidence model
        logger.info("Training confidence model...")
        confidence_model, confidence_metrics = self.train_confidence_model(features_df, confidence_targets)
        
        # Save confidence model
        confidence_predictor = ConfidencePredictor()
        confidence_predictor.save_model(confidence_model)
        
        # Train line model
        logger.info("Training line model...")
        line_model, line_metrics = self.train_line_model(features_df, line_targets)
        
        # Save line model
        line_predictor = LinePredictor()
        line_predictor.save_model(line_model)
        
        return {
            "success": True,
            "confidence_metrics": confidence_metrics,
            "line_metrics": line_metrics,
            "samples_used": len(features_df)
        }

