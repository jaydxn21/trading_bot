# trade_manager.py

import time
import logging
import numpy as np
import mt5_bridge

from utils.indicators import calculate_common_indicators, adx_from_candles

logger = logging.getLogger("trade_manager")


class TradingManager:
    ACTIVE_STRATEGIES = ["crash_boom", "super_scalper", "scalper"]

    EXECUTION_COOLDOWN = 20
    MIN_CONFIDENCE = 30

    BASE_LOT = 0.01
    MAX_LOT = 0.05

    def __init__(self, get_strategy_func):
        self.get_strategy = get_strategy_func
        self.strategies = {}

        self.last_trade_time = 0
        self.current_htf_trend = "neutral"
        self.htf_indicators = {}

        self._load_strategies()

    def _load_strategies(self):
        for name in self.ACTIVE_STRATEGIES:
            strat = self.get_strategy(name)
            if strat:
                self.strategies[name] = strat
                logger.info(f"[INIT] Strategy loaded: {name}")

    # ───────── HTF ─────────
    def update_htf(self, candles):
        if len(candles) < 50:
            self.current_htf_trend = "neutral"
            self.htf_indicators = {}
            return

        closes = np.array([c["close"] for c in candles])
        sma_fast = closes[-9:].mean()
        sma_slow = closes[-21:].mean()

        diff = (sma_fast - sma_slow) / sma_slow * 100
        trend = "bullish" if diff > 0.1 else "bearish" if diff < -0.1 else "neutral"

        self.current_htf_trend = trend
        self.htf_indicators = {"htf_trend": trend}

    def can_execute(self):
        if time.time() - self.last_trade_time < self.EXECUTION_COOLDOWN:
            return False
        if mt5_bridge.has_open_position():
            return False
        return True

    def calculate_lot(self, confidence):
        scale = confidence / 100
        lot = self.BASE_LOT + (self.MAX_LOT - self.BASE_LOT) * scale
        return round(lot, 2)

    # ───────── MAIN LOOP ─────────
    def run_cycle(self, candles, price, symbol):
        self.update_htf(candles)

        highs = np.array([c["high"] for c in candles])
        lows = np.array([c["low"] for c in candles])
        closes = np.array([c["close"] for c in candles])

        indicators = calculate_common_indicators(highs, lows, closes)
        indicators["symbol"] = symbol
        indicators.update(self.htf_indicators)

        for name in self.ACTIVE_STRATEGIES:
            strat = self.strategies[name]

            sig = strat.analyze_market(
                candles=candles,
                current_price=price,
                indicators=indicators
            )

            if sig["signal"] == "hold":
                continue

            # 🔥 Crash/Boom bypasses filters
            if name == "crash_boom":
                return self._execute(sig, name, price)

            if sig["confidence"] < self.MIN_CONFIDENCE:
                continue

            if not self.can_execute():
                continue

            return self._execute(sig, name, price)

        return {"signal": "hold"}

    def _execute(self, sig, strategy, price):
        lot = self.calculate_lot(sig.get("confidence", 50))
        payload = {
            "action": sig["signal"].upper(),
            "confidence": sig.get("confidence", 50),
            "strategy": strategy,
            "price": price
        }

        if mt5_bridge.write_signal(payload):
            self.last_trade_time = time.time()
            logger.info(
                f"🚀 EXECUTED {payload['action']} | "
                f"Strategy={strategy} | "
                f"Conf={payload['confidence']}%"
            )

        sig["strategy"] = strategy
        sig["lot"] = lot
        return sig
