"""
Over/Under Feature Engineering - Extracts features for over/under ML models
"""

from typing import Dict, Any, Optional
from datetime import datetime
from .over_under_service import LiveGame, TeamStats
from .nba_api_service import NBADataService


class OverUnderFeatureEngineer:
    """Extracts and normalizes features for over/under total prediction models"""
    
    @staticmethod
    def build_feature_set(
        live_game: LiveGame,
        team_stats: Dict[str, TeamStats],
        current_pace: float,
        expected_pace: float,
        time_elapsed: float,
        time_remaining: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Build feature set for over/under ML model
        
        Args:
            live_game: Current game state
            team_stats: Dictionary mapping team names to TeamStats
            current_pace: Current scoring pace (points per 48 min)
            expected_pace: Expected pace based on season averages
            time_elapsed: Minutes elapsed in game
            time_remaining: Minutes remaining in game
            additional_context: Optional additional context (injuries, rest days, etc.)
            
        Returns:
            Dictionary of normalized features for ML model
        """
        home_stats = team_stats.get(live_game.home_team)
        away_stats = team_stats.get(live_game.away_team)
        
        # Basic game state features
        features = {
            # Current game state
            'current_total': float(live_game.home_score + live_game.away_score),
            'home_score': float(live_game.home_score),
            'away_score': float(live_game.away_score),
            'score_differential': float(abs(live_game.home_score - live_game.away_score)),
            'quarter': float(live_game.quarter),
            'time_elapsed': time_elapsed,
            'time_remaining': time_remaining,
            'time_elapsed_pct': time_elapsed / 48.0 if time_elapsed > 0 else 0.0,
            
            # Pace features
            'current_pace': current_pace,
            'expected_pace': expected_pace,
            'pace_differential': current_pace - expected_pace,
            'pace_ratio': current_pace / expected_pace if expected_pace > 0 else 1.0,
            
            # Team statistics
            'home_ppg': home_stats.ppg if home_stats else 112.5,
            'away_ppg': away_stats.ppg if away_stats else 112.5,
            'combined_ppg': (home_stats.ppg if home_stats else 112.5) + (away_stats.ppg if away_stats else 112.5),
            'home_pace': home_stats.pace if home_stats else 100.0,
            'away_pace': away_stats.pace if away_stats else 100.0,
            'combined_pace': (home_stats.pace if home_stats else 100.0) + (away_stats.pace if away_stats else 100.0),
            
            # Scoring rate features
            'points_per_minute': (live_game.home_score + live_game.away_score) / time_elapsed if time_elapsed > 0 else 0.0,
            'projected_at_current_pace': (current_pace / 48.0) * time_remaining if time_remaining > 0 else 0.0,
        }
        
        # Contextual features
        if additional_context:
            features.update({
                'home_rest_days': float(additional_context.get('home_rest_days', 1.0)),
                'away_rest_days': float(additional_context.get('away_rest_days', 1.0)),
                'is_back_to_back_home': 1.0 if additional_context.get('home_back_to_back', False) else 0.0,
                'is_back_to_back_away': 1.0 if additional_context.get('away_back_to_back', False) else 0.0,
                'is_playoff': 1.0 if additional_context.get('is_playoff', False) else 0.0,
            })
        else:
            features.update({
                'home_rest_days': 1.0,
                'away_rest_days': 1.0,
                'is_back_to_back_home': 0.0,
                'is_back_to_back_away': 0.0,
                'is_playoff': 0.0,
            })
        
        # Game situation features
        features.update({
            'is_close_game': 1.0 if abs(live_game.home_score - live_game.away_score) < 10 else 0.0,
            'is_blowout': 1.0 if abs(live_game.home_score - live_game.away_score) > 20 else 0.0,
            'is_late_game': 1.0 if live_game.quarter >= 4 and time_remaining < 8 else 0.0,
            'is_very_late': 1.0 if live_game.quarter >= 4 and time_remaining < 3 else 0.0,
            'is_overtime': 1.0 if live_game.quarter > 4 else 0.0,
        })
        
        return features
    
    @staticmethod
    def normalize_features(features: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize features to 0-1 range for ML models
        
        Args:
            features: Raw feature dictionary
            
        Returns:
            Normalized feature dictionary
        """
        # Define normalization ranges (min, max) for each feature
        # These should ideally be learned from training data, but we'll use reasonable defaults
        normalization_ranges = {
            'current_total': (0, 300),
            'home_score': (0, 150),
            'away_score': (0, 150),
            'score_differential': (0, 50),
            'quarter': (1, 7),  # Up to 3 OTs
            'time_elapsed': (0, 60),  # Including OTs
            'time_remaining': (0, 48),
            'time_elapsed_pct': (0, 1),
            'current_pace': (80, 150),
            'expected_pace': (80, 150),
            'pace_differential': (-30, 30),
            'pace_ratio': (0.5, 1.5),
            'home_ppg': (90, 130),
            'away_ppg': (90, 130),
            'combined_ppg': (180, 260),
            'home_pace': (85, 115),
            'away_pace': (85, 115),
            'combined_pace': (170, 230),
            'points_per_minute': (0, 10),
            'projected_at_current_pace': (0, 150),
            'home_rest_days': (0, 5),
            'away_rest_days': (0, 5),
        }
        
        normalized = {}
        for key, value in features.items():
            if key in normalization_ranges:
                min_val, max_val = normalization_ranges[key]
                if max_val > min_val:
                    normalized[key] = (value - min_val) / (max_val - min_val)
                    # Clamp to [0, 1]
                    normalized[key] = max(0.0, min(1.0, normalized[key]))
                else:
                    normalized[key] = 0.5  # Default if range is invalid
            else:
                # Binary features or features without defined range - keep as is
                normalized[key] = value
        
        return normalized

