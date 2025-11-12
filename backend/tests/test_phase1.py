"""
Test script for Phase 1: Infrastructure & Enhanced Data Collection
"""
import sys
from datetime import date, datetime
from app.database import SessionLocal, engine, Base
from app.models.player_context import PlayerContext
from app.models.market_context import MarketContext
from app.models.ai_features import AIFeatureSet
from app.services.context_collector import ContextCollector
from app.services.market_data_service import MarketDataService
from app.services.feature_engineer import FeatureEngineer

def test_database_models():
    """Test that database models can be created"""
    print("Testing database models...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✓ Database models created successfully")
        return True
    except Exception as e:
        print(f"✗ Error creating database models: {e}")
        return False

def test_context_collector():
    """Test ContextCollector service"""
    print("\nTesting ContextCollector...")
    try:
        # Test rest days calculation (using a known player)
        test_player_id = 2544  # LeBron James
        test_date = date.today()
        
        rest_days = ContextCollector.calculate_rest_days(test_player_id, test_date, "2024-25")
        print(f"✓ Rest days calculation: {rest_days} days")
        
        # Test matchup history
        matchup_info = ContextCollector.get_matchup_history(test_player_id, 1610612747, "2024-25", 5)
        print(f"✓ Matchup history: {matchup_info}")
        
        # Test injury status
        injury_info = ContextCollector.get_injury_status(test_player_id, test_date)
        print(f"✓ Injury status: {injury_info}")
        
        # Test full context collection
        context = ContextCollector.collect_player_context(
            test_player_id, test_date, 1610612747, True, "2024-25"
        )
        print(f"✓ Player context collected: rest_days={context.rest_days}, is_home={context.is_home_game}")
        
        return True
    except Exception as e:
        print(f"✗ Error in ContextCollector: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_market_data_service():
    """Test MarketDataService"""
    print("\nTesting MarketDataService...")
    try:
        test_player_id = 2544
        test_date = date.today()
        prop_type = "PTS"
        
        # Test fair line calculation
        fair_line = MarketDataService.calculate_fair_line(test_player_id, prop_type, "2024-25")
        print(f"✓ Fair line calculation: {fair_line}")
        
        # Test market context creation
        market_context = MarketDataService.get_or_create_market_context(
            test_player_id, prop_type, test_date, market_line=25.5
        )
        print(f"✓ Market context created: line={market_context.market_line}, fair_line={market_context.fair_line}")
        
        return True
    except Exception as e:
        print(f"✗ Error in MarketDataService: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_feature_engineer():
    """Test FeatureEngineer service"""
    print("\nTesting FeatureEngineer...")
    try:
        test_player_id = 2544
        test_date = date.today()
        prop_type = "PTS"
        
        # Test stat features extraction
        stat_features = FeatureEngineer.extract_player_stat_features(
            test_player_id, prop_type, "2024-25", 10
        )
        print(f"✓ Stat features extracted: {list(stat_features.keys())}")
        if stat_features:
            print(f"  - Rolling avg 10: {stat_features.get('rolling_avg_10')}")
            print(f"  - Trend: {stat_features.get('trend')}")
        
        # Test context features extraction
        context_features = FeatureEngineer.extract_context_features(
            test_player_id, test_date, 1610612747, True, "2024-25"
        )
        print(f"✓ Context features extracted: {list(context_features.keys())}")
        
        # Test market features extraction
        market_features = FeatureEngineer.extract_market_features(
            test_player_id, prop_type, test_date, 25.5
        )
        print(f"✓ Market features extracted: {list(market_features.keys())}")
        
        # Test historical performance features
        hist_features = FeatureEngineer.extract_historical_performance_features(
            test_player_id, prop_type, 25.5, "2024-25"
        )
        print(f"✓ Historical features extracted: {list(hist_features.keys())}")
        if hist_features:
            print(f"  - Hit rate over: {hist_features.get('hit_rate_over')}")
        
        # Test complete feature set
        feature_set = FeatureEngineer.build_feature_set(
            test_player_id, prop_type, test_date, 25.5, 1610612747, True, "2024-25"
        )
        print(f"✓ Complete feature set built: {len(feature_set)} features")
        
        # Test normalization
        normalized = FeatureEngineer.normalize_features(feature_set)
        print(f"✓ Features normalized: {len(normalized)} features")
        
        return True
    except Exception as e:
        print(f"✗ Error in FeatureEngineer: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_operations():
    """Test database operations"""
    print("\nTesting database operations...")
    try:
        db = SessionLocal()
        
        # Test PlayerContext creation
        context = PlayerContext(
            player_id=2544,
            game_date=date.today(),
            rest_days=1,
            is_home_game=True,
            opponent_team_id=1610612747
        )
        db.add(context)
        db.commit()
        print(f"✓ PlayerContext saved to database: ID={context.id}")
        
        # Test MarketContext creation
        market = MarketContext(
            player_id=2544,
            game_date=date.today(),
            prop_type="PTS",
            market_line=25.5,
            fair_line=26.0
        )
        db.add(market)
        db.commit()
        print(f"✓ MarketContext saved to database: ID={market.id}")
        
        # Test AIFeatureSet creation
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
        print(f"✓ AIFeatureSet saved to database: ID={features.id}")
        
        db.close()
        return True
    except Exception as e:
        print(f"✗ Error in database operations: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 1 Testing: Infrastructure & Enhanced Data Collection")
    print("=" * 60)
    
    results = []
    results.append(("Database Models", test_database_models()))
    results.append(("ContextCollector", test_context_collector()))
    results.append(("MarketDataService", test_market_data_service()))
    results.append(("FeatureEngineer", test_feature_engineer()))
    results.append(("Database Operations", test_database_operations()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All Phase 1 tests passed!")
    else:
        print("✗ Some tests failed. Please review errors above.")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

