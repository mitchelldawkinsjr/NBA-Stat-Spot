"""
Test script for Phase 1 & 2: Infrastructure, Data Collection, and ML Models
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
from app.services.prop_engine import PropBetEngine
from app.services.nba_api_service import NBADataService

def test_phase1_models():
    """Test Phase 1 database models"""
    print("=" * 60)
    print("Phase 1: Testing Database Models")
    print("=" * 60)
    
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Database models created successfully")
        
        db = SessionLocal()
        
        # Test PlayerContext
        context = PlayerContext(
            player_id=2544,
            game_date=date.today(),
            rest_days=1,
            is_home_game=True,
            opponent_team_id=1610612747
        )
        db.add(context)
        db.commit()
        print(f"✓ PlayerContext saved: ID={context.id}")
        
        # Test MarketContext
        market = MarketContext(
            player_id=2544,
            game_date=date.today(),
            prop_type="PTS",
            market_line=25.5,
            fair_line=26.0
        )
        db.add(market)
        db.commit()
        print(f"✓ MarketContext saved: ID={market.id}")
        
        # Test AIFeatureSet
        features = AIFeatureSet(
            player_id=2544,
            game_date=date.today(),
            prop_type="PTS",
            rolling_avg_10=25.5,
            rolling_avg_5=26.0,
            trend="up"
        )
        db.add(features)
        db.commit()
        print(f"✓ AIFeatureSet saved: ID={features.id}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Error testing models: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase1_services():
    """Test Phase 1 services"""
    print("\n" + "=" * 60)
    print("Phase 1: Testing Services")
    print("=" * 60)
    
    try:
        test_player_id = 2544  # LeBron James
        test_date = date.today()
        
        # Test ContextCollector
        print("\nTesting ContextCollector...")
        rest_days = ContextCollector.calculate_rest_days(test_player_id, test_date, "2024-25")
        print(f"✓ Rest days: {rest_days}")
        
        context = ContextCollector.collect_player_context(
            test_player_id, test_date, 1610612747, True, "2024-25"
        )
        print(f"✓ Context collected: rest_days={context.rest_days}")
        
        # Test MarketDataService
        print("\nTesting MarketDataService...")
        fair_line = MarketDataService.calculate_fair_line(test_player_id, "PTS", "2024-25")
        print(f"✓ Fair line: {fair_line}")
        
        market_context = MarketDataService.get_or_create_market_context(
            test_player_id, "PTS", test_date, market_line=25.5
        )
        print(f"✓ Market context: line={market_context.market_line}")
        
        # Test FeatureEngineer
        print("\nTesting FeatureEngineer...")
        stat_features = FeatureEngineer.extract_player_stat_features(
            test_player_id, "PTS", "2024-25", 10
        )
        print(f"✓ Stat features: {len(stat_features)} features")
        
        feature_set = FeatureEngineer.build_feature_set(
            test_player_id, "PTS", test_date, 25.5, 1610612747, True, "2024-25"
        )
        print(f"✓ Complete feature set: {len(feature_set)} features")
        
        normalized = FeatureEngineer.normalize_features(feature_set)
        print(f"✓ Normalized features: {len(normalized)} features")
        
        return True
    except Exception as e:
        print(f"✗ Error testing services: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase2_ml_models():
    """Test Phase 2 ML models"""
    print("\n" + "=" * 60)
    print("Phase 2: Testing ML Models")
    print("=" * 60)
    
    try:
        # Test ModelServer
        print("\nTesting ModelServer...")
        model_server = get_model_server()
        print(f"✓ ModelServer initialized")
        
        # Test health check
        health = model_server.health_check()
        print(f"✓ Health check: confidence={health['confidence_model']['available']}, line={health['line_model']['available']}")
        
        # Test feature set for prediction
        test_player_id = 2544
        test_date = date.today()
        
        feature_set = FeatureEngineer.build_feature_set(
            test_player_id, "PTS", test_date, 25.5, 1610612747, True, "2024-25"
        )
        normalized_features = FeatureEngineer.normalize_features(feature_set)
        
        # Test predictions (will return None if models not trained yet)
        print("\nTesting ML Predictions...")
        ml_confidence = model_server.predict_confidence(normalized_features)
        ml_line = model_server.predict_line(normalized_features)
        
        if ml_confidence is not None:
            print(f"✓ ML Confidence prediction: {ml_confidence}")
        else:
            print("⚠ ML Confidence model not available (needs training)")
        
        if ml_line is not None:
            print(f"✓ ML Line prediction: {ml_line}")
        else:
            print("⚠ ML Line model not available (needs training)")
        
        # Test evaluate_prop_with_ml
        print("\nTesting evaluate_prop_with_ml...")
        logs = NBADataService.fetch_player_game_log(test_player_id, "2024-25")
        if logs:
            result = PropBetEngine.evaluate_prop_with_ml(
                logs, "pts", 25.5, "over",
                player_id=test_player_id,
                game_date=test_date,
                opponent_team_id=1610612747,
                is_home_game=True,
                season="2024-25"
            )
            print(f"✓ Prop evaluation: confidence={result.get('confidence')}, ml_available={result.get('ml_available')}")
            print(f"  - Confidence source: {result.get('confidence_source', 'rule_based')}")
        else:
            print("⚠ No game logs available for testing")
        
        return True
    except Exception as e:
        print(f"✗ Error testing ML models: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Testing Phases 1 & 2: Infrastructure & ML Models")
    print("=" * 60)
    
    results = []
    results.append(("Phase 1: Database Models", test_phase1_models()))
    results.append(("Phase 1: Services", test_phase1_services()))
    results.append(("Phase 2: ML Models", test_phase2_ml_models()))
    
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
        print("✗ Some tests failed. Please review errors above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

