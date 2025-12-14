# bot.py — Modular Trading Bot with HTF support
import logging
import time
import numpy as np
from datetime import datetime
from trade_manager import TradingManager
from strategies.scalper import ScalperStrategy
from strategies.super_scalper import SuperScalperStrategy
from utils.indicators import calculate_common_indicators

# -------------------------
# Logger setup
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------------
# Strategy registry
# -------------------------
STRATEGY_CLASSES = {
    "scalper": ScalperStrategy,
    "super_scalper": SuperScalperStrategy
}

# Factory function for TradingManager
def get_strategy_instance(name: str):
    cls = STRATEGY_CLASSES.get(name)
    if cls:
        return cls()
    return None

# -------------------------
# Simulated candle feed
# -------------------------
def generate_mock_candles(num=120, start_price=1000):
    """Generate mock OHLCV candles for testing"""
    candles = []
    price = start_price
    for i in range(num):
        change = np.random.normal(0, 0.3)  # small random walk
        open_p = price
        close_p = max(1, price + change)
        high_p = max(open_p, close_p) + np.random.random() * 0.2
        low_p = min(open_p, close_p) - np.random.random() * 0.2
        volume = np.random.randint(10, 100)
        candles.append({
            "timestamp": int(time.time()) - (num-i)*60,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume
        })
        price = close_p
    return candles

# -------------------------
# Bot main loop
# -------------------------
def main():
    active_strategies = ["scalper", "super_scalper"]
    manager = TradingManager(get_strategy_func=get_strategy_instance)

    # Simulate live feed
    candles = generate_mock_candles(150)
    current_price = candles[-1]["close"]

    while True:
        # In a real bot, fetch latest candle from exchange API
        # For simulation, append a new mock candle
        new_candle = generate_mock_candles(1, start_price=current_price)[0]
        candles.append(new_candle)
        if len(candles) > 200:
            candles = candles[-200:]

        current_price = new_candle["close"]

        # Run trading cycle
        signal = manager.run_cycle(candles, current_price)

        # Logging output
        if signal["signal"] not in ["hold", "HOLD"]:
            logger.info(
                f"TRADE SIGNAL: {signal['signal'].upper()} | "
                f"Price: {current_price:.2f} | "
                f"Conf: {signal['confidence']}% | "
                f"Strategy: {signal['strategy']} | "
                f"HTF: {manager.current_htf_trend}({manager.last_htf_strength})"
            )
        else:
            logger.info(
                f"HOLD | Price: {current_price:.2f} | "
                f"HTF: {manager.current_htf_trend}({manager.last_htf_strength})"
            )

        time.sleep(2)  # simulate wait for next candle (2 seconds for testing)

if __name__ == "__main__":
    main()
