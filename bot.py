# bot.py

import logging
import time
import numpy as np
import requests
from datetime import datetime

from trade_manager import TradingManager
from strategies.scalper import ScalperStrategy
from strategies.super_scalper import SuperScalperStrategy
from strategies.crash_boom import CrashBoomStrategy

# -------------------------
# Config
# -------------------------
JOURNAL_ENDPOINT = "http://127.0.0.1:8085/journal"
SYMBOL = "Crash 1000 Index"

# -------------------------
# Logger
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
    "crash_boom": CrashBoomStrategy,
    "super_scalper": SuperScalperStrategy,
    "scalper": ScalperStrategy,
}

def get_strategy_instance(name):
    cls = STRATEGY_CLASSES.get(name)
    return cls() if cls else None

# -------------------------
# Candle generator
# -------------------------
def generate_mock_candles(num=120, start_price=1000):
    candles = []
    price = start_price
    for _ in range(num):
        change = np.random.normal(0, 0.6)
        open_p = price
        close_p = max(1, price + change)
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 0.3))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 0.3))
        candles.append({
            "timestamp": int(time.time()),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p
        })
        price = close_p
    return candles

# -------------------------
# Journal
# -------------------------
def journal_trade(event, ticket, symbol, volume, price, strategy):
    payload = {
        "time": datetime.utcnow().isoformat(),
        "event": event,
        "ticket": ticket,
        "symbol": symbol,
        "volume": volume,
        "price": price,
        "strategy": strategy
    }
    try:
        requests.post(JOURNAL_ENDPOINT, json=payload, timeout=5)
    except Exception as e:
        logger.warning(f"Journal failed: {e}")

# -------------------------
# Main loop
# -------------------------
def main():
    manager = TradingManager(get_strategy_func=get_strategy_instance)

    candles = generate_mock_candles(150)
    price = candles[-1]["close"]

    while True:
        new = generate_mock_candles(1, start_price=price)[0]
        candles.append(new)
        candles = candles[-200:]
        price = new["close"]

        signal = manager.run_cycle(
            candles=candles,
            price=price,
            symbol=SYMBOL
        )

        if signal["signal"] != "hold":
            logger.warning(
                f"🚀 {signal['signal'].upper()} | "
                f"{SYMBOL} @ {price:.2f} | "
                f"Conf={signal['confidence']}% | "
                f"Strategy={signal['strategy']}"
            )

            journal_trade(
                event=signal["signal"].upper(),
                ticket=int(time.time()),
                symbol=SYMBOL,
                volume=signal.get("lot", 1.0),
                price=price,
                strategy=signal["strategy"]
            )
        else:
            logger.info(f"HOLD | {SYMBOL} | Price={price:.2f}")

        time.sleep(2)

if __name__ == "__main__":
    main()
