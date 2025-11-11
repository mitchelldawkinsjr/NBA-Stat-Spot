# backend/app/services/over_under_service.py
"""
Over/Under Analysis Service
Analyzes live NBA games to recommend over/under bets based on:
- Current game pace vs expected pace
- Time remaining and contextual factors
- Team season averages
"""

from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
import math


class LiveGame:
    """Simple model for live game data"""
    def __init__(
        self,
        game_id: str,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int,
        quarter: int,
        time_remaining: str,
        is_final: bool = False
    ):
        self.game_id = game_id
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = home_score
        self.away_score = away_score
        self.quarter = quarter
        self.time_remaining = time_remaining
        self.is_final = is_final


class TeamStats:
    """Simple model for team season statistics"""
    def __init__(
        self,
        team_name: str,
        ppg: float,
        pace: float = 100.0,
        home_ppg: float = None,
        away_ppg: float = None
    ):
        self.team_name = team_name
        self.ppg = ppg
        self.pace = pace
        self.home_ppg = home_ppg or ppg
        self.away_ppg = away_ppg or ppg


class OverUnderAnalysis:
    """Results of over/under analysis"""
    def __init__(
        self,
        game_id: str,
        current_total: int,
        projected_total: float,
        live_line: Optional[float],
        current_pace: float,
        expected_pace: float,
        quarter: int,
        time_remaining_minutes: float,
        recommendation: str,
        confidence: str,
        edge_percentage: float,
        key_factors: List[str],
        reasoning: str
    ):
        self.game_id = game_id
        self.current_total = current_total
        self.projected_total = projected_total
        self.live_line = live_line
        self.current_pace = current_pace
        self.expected_pace = expected_pace
        self.quarter = quarter
        self.time_remaining_minutes = time_remaining_minutes
        self.recommendation = recommendation
        self.confidence = confidence
        self.edge_percentage = edge_percentage
        self.key_factors = key_factors
        self.reasoning = reasoning

    def to_dict(self):
        return {
            'game_id': self.game_id,
            'current_total': self.current_total,
            'projected_total': round(self.projected_total, 1),
            'live_line': self.live_line,
            'current_pace': round(self.current_pace, 1),
            'expected_pace': round(self.expected_pace, 1),
            'pace_differential': round(self.current_pace - self.expected_pace, 1),
            'quarter': self.quarter,
            'time_remaining_minutes': round(self.time_remaining_minutes, 1),
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'edge_percentage': round(self.edge_percentage, 2),
            'key_factors': self.key_factors,
            'reasoning': self.reasoning
        }


class OverUnderAnalyzer:
    """
    Analyzes live games for over/under betting opportunities
    
    The core logic:
    1. Calculate how much time has elapsed and what the current scoring pace is
    2. Compare to expected pace based on team season averages
    3. Project final total using weighted combination of current + expected pace
    4. Apply contextual adjustments (close game, blowout, late game)
    5. Determine if there's an edge vs the betting line
    """
    
    def __init__(self, team_stats_lookup: dict = None):
        """
        Args:
            team_stats_lookup: Dictionary mapping team names to TeamStats objects
                              If None, will use default averages
        """
        self.team_stats_lookup = team_stats_lookup or self._get_default_stats()
        
    def _get_default_stats(self) -> dict:
        """Default team stats (league average) for testing"""
        return {
            'DEFAULT': TeamStats(team_name='DEFAULT', ppg=112.5, pace=100.0)
        }
    
    def analyze_game(
        self, 
        live_game: LiveGame,
        live_line: Optional[float] = None,
        use_ai: bool = False,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> OverUnderAnalysis:
        """
        Main analysis function
        
        Args:
            live_game: Current game state
            live_line: Current over/under betting line (optional)
            
        Returns:
            OverUnderAnalysis with recommendation and reasoning
        """
        
        # Step 1: Calculate time remaining
        time_remaining = self._calculate_time_remaining(
            live_game.quarter, 
            live_game.time_remaining
        )
        
        # Step 2: Get team season averages
        default_stats = self.team_stats_lookup.get('DEFAULT', TeamStats(team_name='DEFAULT', ppg=112.5, pace=100.0))
        home_stats = self.team_stats_lookup.get(
            live_game.home_team, 
            default_stats
        )
        away_stats = self.team_stats_lookup.get(
            live_game.away_team,
            default_stats
        )
        
        # Step 3: Calculate current pace (points per 48 minutes)
        time_elapsed = 48 - time_remaining
        current_total = live_game.home_score + live_game.away_score
        
        if time_elapsed > 0:
            current_pace = (current_total / time_elapsed) * 48
        else:
            current_pace = 0
        
        # Step 4: Expected pace based on season averages
        expected_pace = home_stats.ppg + away_stats.ppg
        
        # Step 5: Project final total (with optional ML enhancement)
        rule_based_projection = self._project_final_total(
            current_total=current_total,
            time_remaining=time_remaining,
            time_elapsed=time_elapsed,
            current_pace=current_pace,
            expected_pace=expected_pace,
            quarter=live_game.quarter,
            score_differential=abs(live_game.home_score - live_game.away_score)
        )
        
        # Enhance with ML if available and requested
        projected_total = rule_based_projection
        if use_ai:
            ml_projection = self._project_with_ml(
                live_game=live_game,
                team_stats_lookup=self.team_stats_lookup,
                current_pace=current_pace,
                expected_pace=expected_pace,
                time_elapsed=time_elapsed,
                time_remaining=time_remaining,
                additional_context=additional_context
            )
            if ml_projection is not None:
                # Blend ML and rule-based (70% ML, 30% rule-based)
                projected_total = 0.7 * ml_projection + 0.3 * rule_based_projection
        
        # Step 6: Determine recommendation
        recommendation, confidence, edge = self._determine_recommendation(
            projected_total=projected_total,
            live_line=live_line,
            quarter=live_game.quarter,
            time_remaining=time_remaining
        )
        
        # Step 7: Build human-readable reasoning (with optional LLM enhancement)
        key_factors, reasoning = self._build_reasoning(
            current_total=current_total,
            projected_total=projected_total,
            current_pace=current_pace,
            expected_pace=expected_pace,
            live_line=live_line,
            quarter=live_game.quarter,
            score_differential=abs(live_game.home_score - live_game.away_score),
            time_remaining=time_remaining
        )
        
        # Enhance with LLM if available and requested
        if use_ai:
            llm_rationale = self._generate_llm_rationale(
                live_game=live_game,
                projected_total=projected_total,
                live_line=live_line,
                recommendation=recommendation,
                confidence=confidence,
                key_factors=key_factors,
                additional_context=additional_context
            )
            if llm_rationale:
                reasoning = llm_rationale
        
        return OverUnderAnalysis(
            game_id=live_game.game_id,
            current_total=current_total,
            projected_total=projected_total,
            live_line=live_line,
            current_pace=current_pace,
            expected_pace=expected_pace,
            quarter=live_game.quarter,
            time_remaining_minutes=time_remaining,
            recommendation=recommendation,
            confidence=confidence,
            edge_percentage=edge,
            key_factors=key_factors,
            reasoning=reasoning
        )
    
    def _calculate_time_remaining(self, quarter: int, time_str: str) -> float:
        """
        Convert quarter number and time string to total minutes remaining
        
        Args:
            quarter: Current quarter (1-4+)
            time_str: Time in format "MM:SS" (e.g., "10:23")
            
        Returns:
            Total minutes remaining in regulation (excludes OT)
        """
        # Parse time string
        parts = time_str.replace(":", " ").split()
        minutes_in_quarter = int(parts[0]) if len(parts) > 0 else 0
        seconds_in_quarter = int(parts[1]) if len(parts) > 1 else 0
        
        # Calculate remaining time in current quarter
        time_remaining_in_quarter = minutes_in_quarter + (seconds_in_quarter / 60.0)
        
        # Add full quarters remaining (if not in OT)
        if quarter <= 4:
            quarters_remaining = 4 - quarter
            total_remaining = (quarters_remaining * 12) + time_remaining_in_quarter
        else:
            # In overtime - only count current OT period
            total_remaining = time_remaining_in_quarter
        
        return total_remaining
    
    def _project_final_total(
        self,
        current_total: int,
        time_remaining: float,
        time_elapsed: float,
        current_pace: float,
        expected_pace: float,
        quarter: int,
        score_differential: int
    ) -> float:
        """
        Project the final total score using weighted pace calculation
        
        Key insight: Weight current pace more heavily as more time elapses,
        but apply contextual adjustments based on game situation
        
        Args:
            current_total: Combined score so far
            time_remaining: Minutes left in game
            time_elapsed: Minutes already played
            current_pace: Actual scoring rate so far (per 48 min)
            expected_pace: Expected rate based on season averages (per 48 min)
            quarter: Current quarter
            score_differential: Point difference between teams
            
        Returns:
            Projected final total score
        """
        
        # Weight current pace more heavily as game progresses
        # Early game: trust expected pace more
        # Late game: trust actual pace more
        pace_weight = min(time_elapsed / 48.0, 0.85)  # Cap at 85% current pace weight
        
        weighted_pace = (current_pace * pace_weight) + (expected_pace * (1 - pace_weight))
        
        # Calculate projected remaining points at weighted pace
        projected_remaining = (weighted_pace / 48.0) * time_remaining
        
        # Apply contextual adjustments
        adjustment_factor = 1.0
        
        # Factor 1: Close game in 4th quarter
        # Close games have more timeouts, fouls, slower pace
        if quarter == 4 and score_differential < 10 and time_remaining < 8:
            adjustment_factor *= 0.93  # Reduce by 7%
        
        # Factor 2: Blowout games
        # Big leads = bench players = less efficient offense
        if score_differential > 20:
            adjustment_factor *= 0.88  # Reduce by 12%
        elif score_differential > 15:
            adjustment_factor *= 0.92  # Reduce by 8%
        
        # Factor 3: Very late game (under 3 minutes)
        # Excessive fouling, timeouts, reviews slow everything down
        if time_remaining < 3 and quarter >= 4:
            adjustment_factor *= 0.85  # Reduce by 15%
        
        # Factor 4: Overtime
        # Overtime periods tend to be slightly higher scoring (fresher legs, urgency)
        if quarter > 4:
            adjustment_factor *= 1.05  # Increase by 5%
        
        # Apply adjustments
        projected_remaining *= adjustment_factor
        
        return current_total + projected_remaining
    
    def _determine_recommendation(
        self,
        projected_total: float,
        live_line: Optional[float],
        quarter: int,
        time_remaining: float
    ) -> Tuple[str, str, float]:
        """
        Determine betting recommendation based on projected vs line
        
        Args:
            projected_total: Our projected final score
            live_line: Current betting line
            quarter: Current quarter
            time_remaining: Minutes remaining
            
        Returns:
            Tuple of (recommendation, confidence, edge_percentage)
            - recommendation: "OVER", "UNDER", or "NO BET"
            - confidence: "HIGH", "MEDIUM", "LOW"
            - edge_percentage: How much edge we have (as percentage)
        """
        
        # Can't make recommendation without a line
        if not live_line:
            return "NO BET", "N/A", 0.0
        
        # Calculate edge (how much our projection differs from line)
        edge = projected_total - live_line
        edge_percentage = (abs(edge) / live_line) * 100
        
        # Don't bet in first quarter - not enough data
        if quarter < 2:
            return "NO BET", "LOW", edge_percentage
        
        # Don't bet with < 3 min remaining - too much variance
        if time_remaining < 3:
            return "NO BET", "LOW", edge_percentage
        
        # Need meaningful edge to recommend
        if abs(edge) < 3:
            return "NO BET", "LOW", edge_percentage
        
        # Determine recommendation
        recommendation = "OVER" if edge > 0 else "UNDER"
        
        # Determine confidence based on edge size and game progress
        if abs(edge) >= 8 and quarter >= 3:
            confidence = "HIGH"
        elif abs(edge) >= 5 and quarter >= 3:
            confidence = "MEDIUM"
        elif abs(edge) >= 3:
            confidence = "LOW"
        else:
            return "NO BET", "LOW", edge_percentage
        
        return recommendation, confidence, edge_percentage
    
    def _build_reasoning(
        self,
        current_total: int,
        projected_total: float,
        current_pace: float,
        expected_pace: float,
        live_line: Optional[float],
        quarter: int,
        score_differential: int,
        time_remaining: float
    ) -> Tuple[List[str], str]:
        """
        Build human-readable explanation of the analysis
        
        Returns:
            Tuple of (key_factors list, full reasoning string)
        """
        
        key_factors = []
        
        # Pace analysis
        pace_diff_percent = ((current_pace / expected_pace) - 1) * 100 if expected_pace > 0 else 0
        
        if pace_diff_percent > 5:
            key_factors.append(
                f"Game is {pace_diff_percent:.1f}% faster than expected pace"
            )
        elif pace_diff_percent < -5:
            key_factors.append(
                f"Game is {abs(pace_diff_percent):.1f}% slower than expected pace"
            )
        else:
            key_factors.append(
                f"Game pace is on track with expectations"
            )
        
        # Game context
        if score_differential < 8 and quarter >= 3:
            key_factors.append(
                "Close game - expect increased stoppages and fouling late"
            )
        elif score_differential > 20:
            key_factors.append(
                "Blowout - expect reduced efficiency with bench players"
            )
        elif score_differential > 15:
            key_factors.append(
                "Comfortable lead - winning team may slow pace"
            )
        
        # Timing considerations
        if quarter >= 3 and time_remaining < 8:
            key_factors.append(
                "Late game - more commercial breaks and strategic timeouts"
            )
        
        # Line comparison
        if live_line:
            diff = projected_total - live_line
            if abs(diff) >= 5:
                key_factors.append(
                    f"Projected total is {abs(diff):.1f} points "
                    f"{'above' if diff > 0 else 'below'} current line"
                )
        
        # Build full reasoning paragraph
        reasoning = (
            f"Through {quarter} quarter(s), the game has scored {current_total} points. "
            f"The current pace projects to {current_pace:.1f} points per 48 minutes, "
            f"while teams average a combined {expected_pace:.1f} PPG. "
        )
        
        if time_remaining > 0:
            reasoning += (
                f"With {time_remaining:.1f} minutes remaining and adjusting for game context, "
                f"the projected final total is {projected_total:.1f}. "
            )
        
        if live_line:
            diff = projected_total - live_line
            reasoning += f"Current line: {live_line}. "
            
            if diff > 5:
                reasoning += (
                    f"Our projection is {diff:.1f} points higher, suggesting "
                    f"the OVER has value. "
                )
            elif diff < -5:
                reasoning += (
                    f"Our projection is {abs(diff):.1f} points lower, suggesting "
                    f"the UNDER has value. "
                )
            else:
                reasoning += "Line appears fairly priced with no clear edge. "
        
        return key_factors, reasoning
    
    def _project_with_ml(
        self,
        live_game: LiveGame,
        team_stats_lookup: Dict[str, TeamStats],
        current_pace: float,
        expected_pace: float,
        time_elapsed: float,
        time_remaining: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[float]:
        """
        Project final total using ML model if available.
        
        Returns:
            ML prediction if available, None otherwise
        """
        try:
            from .ml_models.model_server import get_model_server
            from .over_under_feature_engineer import OverUnderFeatureEngineer
            
            model_server = get_model_server()
            if not model_server.is_available():
                return None
            
            # Build features
            feature_engineer = OverUnderFeatureEngineer()
            features = feature_engineer.build_feature_set(
                live_game=live_game,
                team_stats=team_stats_lookup,
                current_pace=current_pace,
                expected_pace=expected_pace,
                time_elapsed=time_elapsed,
                time_remaining=time_remaining,
                additional_context=additional_context
            )
            
            # Normalize features
            normalized_features = feature_engineer.normalize_features(features)
            
            # Get ML prediction
            ml_prediction = model_server.predict_total(normalized_features)
            return ml_prediction
            
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("ML prediction failed for over/under", error=str(e))
            return None
    
    def _generate_llm_rationale(
        self,
        live_game: LiveGame,
        projected_total: float,
        live_line: Optional[float],
        recommendation: str,
        confidence: str,
        key_factors: List[str],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Generate LLM-enhanced rationale if available.
        
        Returns:
            LLM rationale if available, None otherwise
        """
        try:
            from .rationale_generator import get_rationale_generator
            
            rationale_generator = get_rationale_generator()
            if not rationale_generator.is_available():
                return None
            
            game_context = {
                'quarter': live_game.quarter,
                'time_remaining': live_game.time_remaining,
                'home_score': live_game.home_score,
                'away_score': live_game.away_score,
            }
            if additional_context:
                game_context.update(additional_context)
            
            llm_rationale = rationale_generator.generate_over_under_rationale(
                home_team=live_game.home_team,
                away_team=live_game.away_team,
                current_total=live_game.home_score + live_game.away_score,
                projected_total=projected_total,
                live_line=live_line,
                recommendation=recommendation,
                confidence=confidence,
                key_factors=key_factors,
                game_context=game_context
            )
            
            return llm_rationale
            
        except Exception as e:
            import structlog
            logger = structlog.get_logger()
            logger.warning("LLM rationale generation failed for over/under", error=str(e))
            return None

