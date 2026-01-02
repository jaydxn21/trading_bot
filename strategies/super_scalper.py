# strategies/super_scalper.py
print("🔥 LOADED SUPER SCALPER FROM:", __file__)

import numpy as np
from datetime import datetime
import logging
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)


class SuperScalperStrategy(BaseStrategy):
    """High-frequency burst trading optimized for R_100 volatility index"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("super_scalper", config or {})
        self.min_confidence = self.config.get("min_confidence", 70)
        self.last_burst_time = None
        self.burst_interval = 10  # minutes
        self.trades_per_burst = 5
        self.target_profit_percent = 20

    # ✅ FIXED SIGNATURE
    def analyze_market(
        self,
        candles: List[Dict[str, Any]],
        current_price: float,
        indicators: Dict[str, Any],
        htf_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:

        # ✅ SAFE HTF INGEST
        self.ingest_htf_context(htf_context)

        if len(candles) < 15:
            return {
                "signal": "hold",
                "price": current_price,
                "confidence": 0,
                "reason": "Insufficient data"
            }

        # Calculate fast R_100 indicators
        calc_indicators = self._calculate_r100_indicators(candles, current_price)
        indicators = {**calc_indicators, **(indicators or {})}

        if self._should_execute_burst() and self._is_good_burst_condition(indicators):
            signal = self._generate_burst_signal(current_price, indicators)
            if signal and signal["signal"] != "hold":
                self.last_burst_time = datetime.now()
                logger.info(
                    f"[SUPER SCALPER] BURST {signal['signal'].upper()} @ {current_price:.2f}"
                )
                return signal

        return {
            "signal": "hold",
            "price": current_price,
            "confidence": 0,
            "reason": "Not in burst mode"
        }

    # ──────────────────────────────────────
    # INTERNAL HELPERS
    # ──────────────────────────────────────

    def _calculate_r100_indicators(self, candles, current_price):
        closes = np.array([c["close"] for c in candles[-30:]])
        highs = np.array([c["high"] for c in candles[-30:]])
        lows = np.array([c["low"] for c in candles[-30:]])

        ma_3 = closes[-3:].mean()
        ma_5 = closes[-5:].mean()
        ma_8 = closes[-8:].mean()

        momentum_3 = (current_price - closes[-3]) / closes[-3] * 100
        momentum_5 = (current_price - closes[-5]) / closes[-5] * 100

        volatility = np.std(closes[-10:]) / np.mean(closes[-10:]) * 100

        recent_high = highs[-10:].max()
        recent_low = lows[-10:].min()
        price_position = (
            (current_price - recent_low) / (recent_high - recent_low) * 100
            if recent_high != recent_low else 50
        )

        price_changes = np.diff(closes[-14:])
        gains = np.clip(price_changes, 0, None)
        losses = np.clip(-price_changes, 0, None)

        avg_gain = gains.mean() if gains.size else 0.001
        avg_loss = losses.mean() if losses.size else 0.001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return {
            "ma_3": ma_3,
            "ma_5": ma_5,
            "ma_8": ma_8,
            "momentum_3": momentum_3,
            "momentum_5": momentum_5,
            "volatility": volatility,
            "price_position": price_position,
            "rsi": rsi
        }

    def _should_execute_burst(self):
        if self.last_burst_time is None:
            return True
        minutes = (datetime.now() - self.last_burst_time).total_seconds() / 60
        return minutes >= self.burst_interval

    def _is_good_burst_condition(self, indicators):
        volatility = indicators["volatility"]
        rsi = indicators["rsi"]
        momentum = indicators["momentum_5"]

        if not (0.5 <= volatility <= 3.0):
            return False
        if abs(momentum) > 2.0:
            return False
        if rsi < 20 or rsi > 80:
            return False
        return True

    def _generate_burst_signal(self, price, indicators):
        buy_score = sell_score = 0

        if indicators["ma_3"] > indicators["ma_5"] > indicators["ma_8"]:
            buy_score += 2
        elif indicators["ma_3"] < indicators["ma_5"] < indicators["ma_8"]:
            sell_score += 2

        if indicators["momentum_3"] > 0.1:
            buy_score += 1
        elif indicators["momentum_3"] < -0.1:
            sell_score += 1

        if 30 < indicators["rsi"] < 50:
            buy_score += 1
        elif 50 < indicators["rsi"] < 70:
            sell_score += 1

        if indicators["price_position"] < 30:
            buy_score += 1
        elif indicators["price_position"] > 70:
            sell_score += 1

        if buy_score >= 3 and buy_score > sell_score:
            return {
                "signal": "buy",
                "price": price,
                "confidence": 75,
                "burst_trades": self.trades_per_burst,
                "target_percent": self.target_profit_percent,
                "strategy": "super_scalper"
            }

        if sell_score >= 3 and sell_score > buy_score:
            return {
                "signal": "sell",
                "price": price,
                "confidence": 75,
                "burst_trades": self.trades_per_burst,
                "target_percent": self.target_profit_percent,
                "strategy": "super_scalper"
            }

        return None
