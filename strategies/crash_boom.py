import logging
import numpy as np
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)


class CrashBoomStrategy(BaseStrategy):
    def __init__(self, config=None):
        super().__init__("crash_boom", config or {})

        self.lookback = 30
        self.spike_multiplier = 2.8
        self.min_adx = 20

        self.boom_rsi = 75
        self.crash_rsi = 25

    def analyze_market(self, candles, current_price, indicators, htf_context=None):
        self.ingest_htf_context(htf_context)
        if len(candles) < self.lookback:
            return {"signal": "hold", "confidence": 0}

        highs = np.array([c["high"] for c in candles[-self.lookback:]])
        lows = np.array([c["low"] for c in candles[-self.lookback:]])
        ranges = highs - lows

        avg_range = np.mean(ranges[:-1])
        last_range = ranges[-1]

        rsi = indicators.get("rsi", 50)
        adx = indicators.get("adx", 0)
        symbol = indicators.get("symbol", "").upper()
        htf_trend = htf_context.get("htf_trend", "neutral") if htf_context else "neutral"

        if adx < self.min_adx:
            return {"signal": "hold", "confidence": 0}

        if last_range < avg_range * self.spike_multiplier:
            return {"signal": "hold", "confidence": 0}

        signal = "hold"
        confidence = 0

        # BOOM → SELL SPIKE
        if "BOOM" in symbol and rsi >= self.boom_rsi:
            if htf_trend != "bullish":
                signal = "sell"
                confidence = self._confidence(last_range / avg_range, rsi - self.boom_rsi)

        # CRASH → BUY SPIKE
        if "CRASH" in symbol and rsi <= self.crash_rsi:
            if htf_trend != "bearish":
                signal = "buy"
                confidence = self._confidence(last_range / avg_range, self.crash_rsi - rsi)

        if signal == "hold":
            return {"signal": "hold", "confidence": 0}

        logger.info(
            f"[CRASH/BOOM] {signal.upper()} | "
            f"Spike={last_range:.2f} Avg={avg_range:.2f} "
            f"RSI={rsi:.1f} ADX={adx:.1f}"
        )

        return {
            "signal": signal,
            "confidence": confidence,
            "strategy": "crash_boom"
        }

    def _confidence(self, spike_ratio, rsi_excess):
        score = 45
        score += min(spike_ratio * 10, 30)
        score += min(abs(rsi_excess) * 2, 20)
        return int(min(score, 95))
