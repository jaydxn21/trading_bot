from typing import List, Dict, Optional, Any
import numpy as np

# ─────────────────────────────────────────────
# Core Scalper Strategy Logic
# ─────────────────────────────────────────────
def run_strategy(
    last_price: float,
    open_trades: List[Dict],
    balance: float,
    candles: List[Dict[str, float]],
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[float]]:
    """
    Simple scalping strategy:
    - Uses short-term momentum (EMA crossover)
    - Looks for very small quick moves
    """

    if not candles or len(candles) < 20:
        return {"action": None, "price": None, "reason": "Insufficient data"}

    closes = np.array([c["close"] for c in candles], dtype=float)

    # Short EMA and Long EMA
    short_ema = np.mean(closes[-5:])
    long_ema = np.mean(closes[-20:])

    # Check if we have an open trade
    has_open_trade = len(open_trades) > 0

    # Buy condition: short EMA crosses above long EMA
    if short_ema > long_ema and not has_open_trade:
        return {"action": "buy", "price": last_price, "reason": "EMA Bullish Cross"}

    # Sell condition: short EMA crosses below long EMA
    if short_ema < long_ema and has_open_trade:
        return {"action": "sell", "price": last_price, "reason": "EMA Bearish Cross"}

    return {"action": None, "price": None, "reason": "No clear signal"}


# ─────────────────────────────────────────────
# Compatibility Wrapper (for bot.py)
# ─────────────────────────────────────────────
def evaluate_trades(
    last_price: float,
    open_trades: List[Dict],
    balance: float,
    candles: List[Dict[str, float]],
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Optional[float]]:
    """
    Wrapper to maintain compatibility with bot.py
    """
    return run_strategy(last_price, open_trades, balance, candles, params)
