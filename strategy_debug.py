# strategy_debug.py - SUPER AGGRESSIVE STRATEGIES FOR CONTINUOUS TESTING
import logging
import random
from typing import List, Dict, Optional
import numpy as np
import time

logger = logging.getLogger(__name__)

# Track last trade to avoid too frequent trading
last_trade_time = 0
TRADE_COOLDOWN = 10  # seconds between trades

def debug_aggressive_strategy(candles: List[Dict], current_price: float, config: Dict = None) -> Dict:
    """
    SUPER aggressive strategy for testing - almost always provides a signal
    """
    global last_trade_time
    
    # Cooldown check
    current_time = time.time()
    if current_time - last_trade_time < TRADE_COOLDOWN:
        return {"signal": "hold", "confidence": 0, "reason": "Cooldown period"}
    
    if len(candles) < 3:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}
    
    # Very simple momentum with high confidence
    recent_closes = [float(c['close']) for c in candles[-3:]]
    price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]
    
    # Always provide a strong signal (very aggressive for testing)
    if price_change >= 0:
        signal = "buy"
        base_confidence = 80
    else:
        signal = "sell" 
        base_confidence = 80
    
    # Add some randomness to confidence for variety
    confidence = random.randint(base_confidence - 10, base_confidence + 10)
    confidence = min(95, max(70, confidence))  # Keep between 70-95%
    
    last_trade_time = current_time
    
    return {
        "signal": signal, 
        "confidence": confidence, 
        "reason": f"Aggressive signal (change: {price_change:.3%})",
        "price_change": price_change
    }

def continuous_trading_strategy(candles: List[Dict], current_price: float) -> Dict:
    """
    Strategy that ensures continuous trading in demo mode
    Alternates between buy and sell with high confidence
    """
    global last_trade_time
    
    current_time = time.time()
    if current_time - last_trade_time < TRADE_COOLDOWN:
        return {"signal": "hold", "confidence": 0, "reason": "Cooldown period"}
    
    # Alternate between buy and sell based on trade count
    trade_count = int(current_time) % 20  # Change every 20 seconds
    
    if trade_count < 10:
        signal = "buy"
        reason = "Continuous trading cycle (buy phase)"
    else:
        signal = "sell"
        reason = "Continuous trading cycle (sell phase)"
    
    confidence = random.randint(75, 90)
    last_trade_time = current_time
    
    return {
        "signal": signal,
        "confidence": confidence,
        "reason": reason,
        "cycle_phase": trade_count
    }

def random_strategy(candles: List[Dict], current_price: float) -> Dict:
    """
    Completely random strategy for stress testing - weighted toward trading
    """
    global last_trade_time
    
    current_time = time.time()
    if current_time - last_trade_time < TRADE_COOLDOWN:
        return {"signal": "hold", "confidence": 0, "reason": "Cooldown period"}
    
    # 80% chance of trade, 20% chance of hold
    signals = ["buy", "sell", "hold"]
    weights = [40, 40, 20]  # 40% buy, 40% sell, 20% hold
    
    signal = random.choices(signals, weights=weights)[0]
    
    if signal == "hold":
        return {"signal": "hold", "confidence": 0, "reason": "Random hold"}
    else:
        confidence = random.randint(70, 95)
        last_trade_time = current_time
        return {
            "signal": signal, 
            "confidence": confidence, 
            "reason": f"Random signal (confidence: {confidence}%)"
        }

def mean_reversion_aggressive(candles: List[Dict], current_price: float, period: int = 10) -> Dict:
    """
    Very aggressive mean reversion strategy
    """
    global last_trade_time
    
    current_time = time.time()
    if current_time - last_trade_time < TRADE_COOLDOWN:
        return {"signal": "hold", "confidence": 0, "reason": "Cooldown period"}
    
    if len(candles) < period:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}
    
    closes = [float(c['close']) for c in candles[-period:]]
    mean_price = np.mean(closes)
    
    # Very sensitive mean reversion
    price_ratio = current_price / mean_price
    
    if price_ratio > 1.001:  # 0.1% above mean -> sell
        signal = "sell"
        confidence = 85
        reason = f"Price {price_ratio:.3%} above mean"
    elif price_ratio < 0.999:  # 0.1% below mean -> buy
        signal = "buy"
        confidence = 85
        reason = f"Price {price_ratio:.3%} below mean"
    else:
        # Even in neutral zone, trade based on very recent movement
        if len(closes) >= 2:
            recent_change = (closes[-1] - closes[-2]) / closes[-2]
            if abs(recent_change) > 0.0005:  # 0.05% movement
                signal = "buy" if recent_change > 0 else "sell"
                confidence = 75
                reason = f"Micro momentum: {recent_change:.3%}"
            else:
                return {"signal": "hold", "confidence": 0, "reason": "No strong signal"}
        else:
            return {"signal": "hold", "confidence": 0, "reason": "Insufficient recent data"}
    
    last_trade_time = current_time
    return {
        "signal": signal,
        "confidence": confidence,
        "reason": reason,
        "price_ratio": price_ratio
    }

def momentum_breaker_strategy(candles: List[Dict], current_price: float) -> Dict:
    """
    Strategy that breaks momentum by providing counter-signals
    Good for testing various market conditions
    """
    global last_trade_time
    
    current_time = time.time()
    if current_time - last_trade_time < TRADE_COOLDOWN:
        return {"signal": "hold", "confidence": 0, "reason": "Cooldown period"}
    
    if len(candles) < 5:
        return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}
    
    # Sometimes go against the trend to test reversal scenarios
    recent_closes = [float(c['close']) for c in candles[-5:]]
    trend = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]
    
    # 70% follow trend, 30% go against trend
    if random.random() < 0.7:
        signal = "buy" if trend > 0 else "sell"
        reason = f"Following trend: {trend:.3%}"
    else:
        signal = "sell" if trend > 0 else "buy"
        reason = f"Counter-trend: {trend:.3%}"
    
    confidence = random.randint(75, 90)
    last_trade_time = current_time
    
    return {
        "signal": signal,
        "confidence": confidence,
        "reason": reason,
        "trend": trend
    }

# Strategy selector for testing different approaches
def get_debug_strategy(strategy_name: str = "aggressive"):
    """Get a debug strategy by name"""
    strategies = {
        "aggressive": debug_aggressive_strategy,
        "continuous": continuous_trading_strategy,
        "random": random_strategy,
        "mean_reversion": mean_reversion_aggressive,
        "momentum_breaker": momentum_breaker_strategy
    }
    
    return strategies.get(strategy_name, debug_aggressive_strategy)

def get_all_strategies():
    """Return all available debug strategies"""
    return {
        "aggressive": debug_aggressive_strategy,
        "continuous": continuous_trading_strategy,
        "random": random_strategy,
        "mean_reversion": mean_reversion_aggressive,
        "momentum_breaker": momentum_breaker_strategy
    }

if __name__ == "__main__":
    # Test the strategies
    test_candles = [
        {"open": 100, "high": 102, "low": 99, "close": 101},
        {"open": 101, "high": 103, "low": 100, "close": 102},
        {"open": 102, "high": 104, "low": 101, "close": 103},
        {"open": 103, "high": 105, "low": 102, "close": 104},
        {"open": 104, "high": 106, "low": 103, "close": 105},
    ]
    
    current_price = 105.5
    
    print("Testing SUPER AGGRESSIVE debug strategies:")
    for name, strategy in get_all_strategies().items():
        result = strategy(test_candles, current_price)
        print(f"{name:15}: {result}")