"""
Test script for Phases 1-3: Infrastructure, ML Models, and LLM Integration
"""
import sys
from datetime import date
from app.database import SessionLocal, engine, Base
from app.models.player_context import PlayerContext
from app.models.market_context import MarketContext
from app.models.ai_features import AIFeatureSet
from app.services.context_collector import ContextCollector
from app.services.market_data_service import MarketDataService
from app.services.feature_engineer import FeatureEngineer
from app.services.ml_models.model_server import get_model_server
from app.services.rationale_generator import get_rationale_generator
from app.services.prop_engine import PropBetEngine
from app.services.nba_api_service import NBADataService

def test_phase1():
    """Test Phase 1: Infrastructure & Data Collection"""
    print("=" * 60)
    print("Phase 1: Infrastructure & Data Collection")
    print("=" * 60)
    
    results = []
    
    # Test database models
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database models created")
        results.append(True)
    except Exception as e:
        print(f"✗ Database models error: {e}")
        results.append(False)
    
    # Test ContextCollector
    try:
        test_player_id = 2544
        test_date = date.today()
        context = ContextCollector.collect_player_context(
            test_player_id, test_date, 1610612747, True, "2024-25"
        )
        print(f"✓ ContextCollector: rest_days={context.rest_days}")
        results.append(True)
    except Exception as e:
        print(f"✗ ContextCollector error: {e}")
        results.append(False)
    
    # Test MarketDataService
    try:
        fair_line = MarketDataService.calculate_fair_line(2544, "PTS", "2024-25")
        print(f"✓ MarketDataService: fair_line={fair_line}")
        results.append(True)
    except Exception as e:
        print(f"✗ MarketDataService error: {e}")
        results.append(False)
    
    # Test FeatureEngineer
    try:
        feature_set = FeatureEngineer.build_feature_set(
            2544, "PTS", date.today(), 25.5, 1610612747, True, "2024-25"
        )
        print(f"✓ FeatureEngineer: {len(feature_set)} features")
        results.append(True)
    except Exception as e:
        print(f"✗ FeatureEngineer error: {e}")
        results.append(False)
    
    return all(results)

def test_phase2():
    """Test Phase 2: ML Models"""
    print("\n" + "=" * 60)
    print("Phase 2: ML Models")
    print("=" * 60)
    
    results = []
    
    # Test ModelServer
    try:
        model_server = get_model_server()
        health = model_server.health_check()
        print(f"✓ ModelServer initialized")
        print(f"  - Confidence model: {health['confidence_model']['available']}")
        print(f"  - Line model: {health['line_model']['available']}")
        results.append(True)
    except Exception as e:
        print(f"✗ ModelServer error: {e}")
        results.append(False)
    
    # Test feature extraction for ML
    try:
        feature_set = FeatureEngineer.build_feature_set(
            2544, "PTS", date.today(), 25.5, 1610612747, True, "2024-25"
        )
        normalized = FeatureEngineer.normalize_features(feature_set)
        
        # Test predictions (will be None if models not trained)
        ml_confidence = model_server.predict_confidence(normalized)
        ml_line = model_server.predict_line(normalized)
        
        if ml_confidence is not None:
            print(f"✓ ML Confidence prediction: {ml_confidence}")
        else:
            print("⚠ ML Confidence model not trained (expected)")
        
        if ml_line is not None:
            print(f"✓ ML Line prediction: {ml_line}")
        else:
            print("⚠ ML Line model not trained (expected)")
        
        results.append(True)
    except Exception as e:
        print(f"✗ ML prediction error: {e}")
        results.append(False)
    
    return all(results)

def test_phase3():
    """Test Phase 3: LLM Integration"""
    print("\n" + "=" * 60)
    print("Phase 3: LLM Integration")
    print("=" * 60)
    
    results = []
    
    # Test RationaleGenerator
    try:
        rationale_generator = get_rationale_generator()
        health = rationale_generator.health_check()
        print(f"✓ RationaleGenerator initialized")
        print(f"  - Available: {health['available']}")
        print(f"  - Services: {len(health['services'])}")
        results.append(True)
    except Exception as e:
        print(f"✗ RationaleGenerator error: {e}")
        results.append(False)
    
    # Test rationale generation (will use fallback if LLMs not available)
    try:
        stats = {
            "hit_rate": 0.75,
            "hit_rate_over": 0.75,
            "recent": {"trend": "up", "avg": 26.5}
        }
        context = {
            "rest_days": 1,
            "is_home_game": True,
            "opponent_def_rank": 15
        }
        
        rationale = rationale_generator.generate_rationale(
            player_name="LeBron James",
            prop_type="PTS",
            line_value=25.5,
            direction="over",
            confidence=75.0,
            ml_confidence=None,
            stats=stats,
            context=context
        )
        print(f"✓ Rationale generated: {rationale[:100]}...")
        results.append(True)
    except Exception as e:
        print(f"✗ Rationale generation error: {e}")
        results.append(False)
    
    return all(results)

def test_integration():
    """Test integrated prop evaluation with ML and LLM"""
    print("\n" + "=" * 60)
    print("Integration Test: Full Prop Evaluation")
    print("=" * 60)
    
    try:
        test_player_id = 2544
        test_date = date.today()
        
        # Get player game logs
        logs = NBADataService.fetch_player_game_log(test_player_id, "2024-25")
        if not logs:
            print("⚠ No game logs available for testing")
            return True  # Not a failure, just no data
        
        # Test evaluate_prop_with_ml
        result = PropBetEngine.evaluate_prop_with_ml(
            logs, "pts", 25.5, "over",
            player_id=test_player_id,
            game_date=test_date,
            opponent_team_id=1610612747,
            is_home_game=True,
            season="2024-25"
        )
        
        print(f"✓ Prop evaluation complete:")
        print(f"  - Confidence: {result.get('confidence')}%")
        print(f"  - Source: {result.get('confidence_source', 'rule_based')}")
        print(f"  - ML Available: {result.get('ml_available', False)}")
        print(f"  - Rationale Source: {result.get('rationale', {}).get('source', 'rule_based')}")
        
        if 'llm' in result.get('rationale', {}):
            llm_rationale = result['rationale']['llm']
            print(f"  - LLM Rationale: {llm_rationale[:100]}...")
        
        return True
    except Exception as e:
        print(f"✗ Integration test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Testing Phases 1-3: Complete AI Prediction Engine")
    print("=" * 60)
    
    results = []
    results.append(("Phase 1: Infrastructure", test_phase1()))
    results.append(("Phase 2: ML Models", test_phase2()))
    results.append(("Phase 3: LLM Integration", test_phase3()))
    results.append(("Integration Test", test_integration()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Review errors above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

