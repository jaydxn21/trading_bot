# strategies/vol_mean_reversion.py
import logging
import numpy as np
from typing import List, Dict, Any
from .base_strategies import BaseStrategy

logger = logging.getLogger(__name__)

class VolMeanReversionStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("vol_mean_reversion", config or {})
        self.bb_period = 20
        self.bb_std = 2.0
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ema_period = 5
        self.max_adx = 20
        self.min_volatility = 0.001
        self.min_confidence = 70

    def analyze_market(self, candles: List[Dict[str, Any]], price: float, indicators: Dict[str, Any]) -> Dict[str, Any]:
        if len(candles) < 50:
            return {"signal": "hold", "confidence": 0, "reason": "Insufficient data"}

        # FIXED: Proper EMA calculation
        closes = np.array([c['close'] for c in candles[-50:]])
        
        # BB
        bb_mid = np.mean(closes[-self.bb_period:])
        bb_std_val = np.std(closes[-self.bb_period:])
        bb_upper = bb_mid + self.bb_std * bb_std_val
        bb_lower = bb_mid - self.bb_std * bb_std_val

        # RSI
        deltas = np.diff(closes[-self.rsi_period - 1:])
        up = deltas.clip(min=0)
        down = np.abs(deltas.clip(max=0))
        roll_up = np.mean(up[:self.rsi_period])
        roll_down = np.mean(down[:self.rsi_period])
        rs = roll_up / roll_down if roll_down else 100
        rsi = 100 - (100 / (1 + rs))

        # FIXED EMA
        alpha = 2 / (self.ema_period + 1)
        ema_fast = closes[-1]
        for price in closes[-self.ema_period:][::-1]:
            ema_fast = alpha * price + (1 - alpha) * ema_fast

        # ADX proxy
        adx = np.std(closes[-14:]) / np.mean(closes[-14:]) * 100
        volatility = np.std(closes[-20:]) / np.mean(closes[-20:])

        # FILTERS
        if adx > self.max_adx:
            return {"signal": "hold", "confidence": 0, "reason": f"Trending market (ADX {adx:.1f})"}
        if volatility < self.min_volatility:
            return {"signal": "hold", "confidence": 0, "reason": f"Low volatility {volatility:.4f}"}

        # SIGNALS
        signal = "hold"
        confidence = 0
        reason = ""

        # BUY
        if price <= bb_lower * 1.005 and rsi < self.rsi_oversold and price > ema_fast:
            confidence = 70 + max(0, (self.rsi_oversold - rsi) * 2)
            signal = "buy"
            reason = f"BB lower + RSI {rsi:.1f} + EMA turn"

        # SELL  
        elif price >= bb_upper * 0.995 and rsi > self.rsi_overbought and price < ema_fast:
            confidence = 70 + max(0, (rsi - self.rsi_overbought) * 2)
            signal = "sell"
            reason = f"BB upper + RSI {rsi:.1f} + EMA turn"

        if confidence >= self.min_confidence:
            logger.info(f"[VOL] {signal.upper()} @ {price:.2f} ({confidence}%) - {reason}")
        else:
            signal = "hold"
            confidence = 0

        return {
            "signal": signal,
            "price": price,
            "confidence": int(confidence),
            "reason": reason or "No signal",
            "strategy": "vol_mean_reversion"
        }