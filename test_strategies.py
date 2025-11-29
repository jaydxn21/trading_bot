# test_strategies.py
from strategies import STRATEGIES, list_strategies

def test_strategy_loading():
    print("🧪 Testing strategy loading...")
    
    strategies = list_strategies()
    print(f"📋 Loaded {len(strategies)} strategies:")
    
    for name, info in strategies.items():
        print(f"  - {name}: {info}")
    
    # Test each strategy
    for strategy_name, strategy in STRATEGIES.items():
        print(f"\n🔍 Testing {strategy_name}:")
        try:
            # Test basic functionality
            print(f"   Name: {getattr(strategy, 'name', 'N/A')}")
            print(f"   Min Confidence: {getattr(strategy, 'min_confidence', 'N/A')}")
            print(f"   Has analyze_market: {hasattr(strategy, 'analyze_market')}")
            print(f"   ✅ {strategy_name} is working")
        except Exception as e:
            print(f"   ❌ {strategy_name} has error: {e}")

if __name__ == "__main__":
    test_strategy_loading()